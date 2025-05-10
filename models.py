from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

Base = declarative_base()

match_team_association = Table(
    'match_team',
    Base.metadata,
    Column('match_id', Integer, ForeignKey('match.id'), primary_key=True),
    Column('team_id', Integer, ForeignKey('team.id'), primary_key=True)
)


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)

    subscribed_events = relationship("Event", secondary="user_event_subscription", back_populates="subscribers")
    subscribed_teams = relationship("Team", secondary="user_team_subscription", back_populates="subscribers")

    def __repr__(self):
        return f"<User(id={self.id})>"


class Event(Base):
    __tablename__ = 'event'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    matches = relationship("Match", back_populates="event", cascade="all, delete-orphan")
    subscribers = relationship("User", secondary="user_event_subscription", back_populates="subscribed_events")

    def __repr__(self):
        return f"<Event(id={self.id}')>"


class Team(Base):
    __tablename__ = 'team'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    matches = relationship("Match", secondary=match_team_association, back_populates="teams")
    subscribers = relationship("User", secondary="user_team_subscription", back_populates="subscribed_teams")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"


class Match(Base):
    __tablename__ = 'match'

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False)
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)

    event = relationship("Event", back_populates="matches")
    teams = relationship("Team", secondary=match_team_association, back_populates="matches")

    def __repr__(self):
        return f"<Match(id={self.id}, start_time='{self.start_time}')>"


class UserEventSubscription(Base):
    __tablename__ = 'user_event_subscription'

    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    event_id = Column(Integer, ForeignKey('event.id'), primary_key=True)


class UserTeamSubscription(Base):
    __tablename__ = 'user_team_subscription'

    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), primary_key=True)


class DatabaseManager:
    def __init__(self, db_url: str = "sqlite:///events.db"):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def get_db(self) -> Session:
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_user(self, user_id: int) -> User:
        with self.SessionLocal() as db:
            user = User(id=user_id)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    def get_user_by_id(self, user_id: int) -> User:
        with self.SessionLocal() as db:
            return db.query(User).filter(User.id == user_id).first()

    def create_event(self, name: str, start_date: datetime = None, end_date: datetime = None) -> Event:
        with self.SessionLocal() as db:
            event = Event(name=name, start_date=start_date, end_date=end_date)
            db.add(event)
            db.commit()
            db.refresh(event)
            return event

    def get_event_by_name(self, name: str) -> Event:
        with self.SessionLocal() as db:
            return db.query(Event).filter(Event.name == name).first()

    def create_team(self, name: str) -> Team:
        with self.SessionLocal() as db:
            team = Team(name=name)
            db.add(team)
            db.commit()
            db.refresh(team)
            return team

    def get_team_by_name(self, name: str) -> Team:
        with self.SessionLocal() as db:
            return db.query(Team).filter(Team.name == name).first()

    def create_match(self, event_id: int, start_time: datetime,
                     team_ids: list[int]) -> Match:
        with self.SessionLocal() as db:
            match = Match(start_time=start_time, event_id=event_id)
            if team_ids:
                teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
                match.teams.extend(teams)
            db.add(match)
            db.commit()
            db.refresh(match)
            return match

    def get_matches_for_user(self, user_id: int) -> tuple[Match]:
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []

            event_matches = db.query(Match).join(Event).join(
                UserEventSubscription,
                UserEventSubscription.event_id == Event.id
            ).filter(UserEventSubscription.user_id == user_id).all()

            team_matches = db.query(Match).join(match_team_association).join(
                Team
            ).join(
                UserTeamSubscription,
                UserTeamSubscription.team_id == Team.id
            ).filter(UserTeamSubscription.user_id == user_id).all()

            all_matches = {match.id: match for match in event_matches + team_matches}
            return [match for match in event_matches + team_matches]

    def subscribe_user_to_event(self, user_id: int, event_id: int) -> bool:
        with self.SessionLocal() as db:
            if db.query(UserEventSubscription).filter_by(
                    user_id=user_id, event_id=event_id
            ).first():
                return False

            subscription = UserEventSubscription(user_id=user_id, event_id=event_id)
            db.add(subscription)
            db.commit()
            return True

    def subscribe_user_to_team(self, user_id: int, team_id: int) -> bool:
        with self.SessionLocal() as db:
            if db.query(UserTeamSubscription).filter_by(
                    user_id=user_id, team_id=team_id
            ).first():
                return False

            subscription = UserTeamSubscription(user_id=user_id, team_id=team_id)
            db.add(subscription)
            db.commit()
            return True

    def unsubscribe_user_from_event(self, user_id: int, event_id: int) -> bool:
        with self.SessionLocal() as db:
            subscription = db.query(UserEventSubscription).filter_by(
                user_id=user_id, event_id=event_id
            ).first()
            if not subscription:
                return False

            db.delete(subscription)
            db.commit()
            return True

    def unsubscribe_user_from_team(self, user_id: int, team_id: int) -> bool:
        with self.SessionLocal() as db:
            subscription = db.query(UserTeamSubscription).filter_by(
                user_id=user_id, team_id=team_id
            ).first()
            if not subscription:
                return False

            db.delete(subscription)
            db.commit()
            return True

if __name__ == "__main__":
    db_manager = DatabaseManager()

    user = db_manager.create_user(123123)
    event = db_manager.create_event("World Championship", datetime(2025, 12, 1, 12, 0, 0))
    event2 = db_manager.create_event("World Championship2", datetime(2026, 2, 12, 1, 0, 0))
    team1 = db_manager.create_team("Team 1")
    team2 = db_manager.create_team("Team 2")
    team3 = db_manager.create_team("Team 3")
    team4 = db_manager.create_team("Team 4")
    team5 = db_manager.create_team("Team 5")

    match = db_manager.create_match(
        event.id,
        datetime(2023, 12, 15, 20, 0),
        [team1.id, team2.id]
    )

    match = db_manager.create_match(
        event2.id,
        datetime(2023, 12, 15, 20, 0),
        [team3.id, team4.id]
    )

    match = db_manager.create_match(
        event2.id,
        datetime(2023, 12, 15, 20, 0),
        [team1.id, team5.id]
    )

    db_manager.subscribe_user_to_event(user.id, event.id)
    db_manager.subscribe_user_to_team(user.id, team5.id)

    user_matches = db_manager.get_matches_for_user(user.id)
    print(f"User's matches: {user_matches}")