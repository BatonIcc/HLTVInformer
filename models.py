from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session, joinedload

Base = declarative_base()

match_team_association = Table(
    'match_team',
    Base.metadata,
    Column('match_id', Integer, ForeignKey('match.id', ondelete="CASCADE"), primary_key=True),
    Column('team_id', Integer, ForeignKey('team.id', ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    is_admin = Column(Boolean, default=False)
    time_zone = Column(Integer)

    subscribed_events = relationship("Event", secondary="user_event_subscription", back_populates="subscribers")
    subscribed_teams = relationship("Team", secondary="user_team_subscription", back_populates="subscribers")

    def __repr__(self):
        return f"<User(id={self.id})>"


class Event(Base):
    __tablename__ = 'event'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    matches = relationship(
        "Match",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    subscribers = relationship(
        "User",
        secondary="user_event_subscription",
        back_populates="subscribed_events"
    )

    def __repr__(self):
        return f"<Event(id={self.id}')>"


class Team(Base):
    __tablename__ = 'team'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    matches = relationship(
        "Match",
        secondary=match_team_association,
        back_populates="teams",
        passive_deletes=True
    )

    subscribers = relationship(
        "User",
        secondary="user_team_subscription",
        back_populates="subscribed_teams"
    )

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"


class Match(Base):
    __tablename__ = 'match'

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=True)
    url = Column(String, nullable=False, unique=True)
    format = Column(String)
    ongoing = Column(Boolean)
    notified = Column(Boolean)
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)

    event = relationship("Event", back_populates="matches")
    teams = relationship("Team", secondary=match_team_association, back_populates="matches")
    streams = relationship("Stream", back_populates="match", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Match(id={self.id}, start_time='{self.start_time}')>"


class Stream(Base):
    __tablename__ = 'stream'

    id = Column(Integer, primary_key=True, autoincrement=True)
    link = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    match_id = Column(Integer, ForeignKey('match.id', ondelete="CASCADE"), nullable=False)

    match = relationship("Match", back_populates="streams")

    def __repr__(self):
        return f"<Stream(id={self.id}, link='{self.link}')>"

class UserEventSubscription(Base):
    __tablename__ = 'user_event_subscription'

    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), primary_key=True)
    event_id = Column(Integer, ForeignKey('event.id', ondelete="CASCADE"), primary_key=True)


class UserTeamSubscription(Base):
    __tablename__ = 'user_team_subscription'

    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id', ondelete="CASCADE"), primary_key=True)


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
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                user = User(id=user_id)
                db.add(user)
                db.commit()
                db.refresh(user)
            return user

    def get_user_by_id(self, user_id: int) -> User:
        with self.SessionLocal() as db:
            return db.query(User).filter(User.id == user_id).first()

    def update_event(self, name: str, start_date: datetime = None, end_date: datetime = None) -> Event:
        with self.SessionLocal() as db:
            event = db.query(Event).filter(Event.name == name).first()
            if not event:
                return self.create_event(name, start_date, end_date)
            event.start_date = start_date
            event.end_date = end_date
            db.commit()
            db.refresh(event)
            return event

    def create_event(self, name: str, start_date: datetime = None, end_date: datetime = None) -> Event:
        with self.SessionLocal() as db:
            event = db.query(Event).filter(Event.name == name).first()
            if not event:
                event = Event(name=name, start_date=start_date, end_date=end_date)
                db.add(event)
                db.commit()
                db.refresh(event)
            return event

    def get_event_by_id(self, id: int) -> Event:
        with self.SessionLocal() as db:
            return db.query(Event).filter(Event.id == id).first()

    def get_event_by_name(self, name: str) -> Event:
        with self.SessionLocal() as db:
            return db.query(Event).filter(Event.name == name).first()

    def create_team(self, name: str) -> Team:
        with self.SessionLocal() as db:
            team = db.query(Team).filter(Team.name == name).first()
            if not team:
                team = Team(name=name)
                db.add(team)
                db.commit()
                db.refresh(team)
            return team

    def get_team_by_id(self, id: int) -> Team:
        with self.SessionLocal() as db:
            return db.query(Team).filter(Team.id == id).first()

    def get_team_by_name(self, name: str) -> Team:
        with self.SessionLocal() as db:
            return db.query(Team).filter(Team.name == name).first()

    def create_match(self, event_name: str, team_names: list[str], url: str, format: str,
                     ongoing: bool , start_time: datetime = None) -> Match:
        with self.SessionLocal() as db:
            match = db.query(Match).filter(Match.url == url).first()
            if not match:
                event = db.query(Event).filter(Event.name == event_name).first()
                if not event:
                    print(event_name, url, start_time)
                    return
                match = Match(start_time=start_time, event_id=event.id, url=url, format=format,
                              ongoing=ongoing, notified=False)
                if team_names:
                    teams = db.query(Team).filter(Team.name.in_(team_names)).all()
                    match.teams.extend(teams)
                db.add(match)
                db.commit()
                db.refresh(match)
            return match

    def update_match(self, event_name: str, team_names: list[str], url: str, format: str,
                     ongoing: bool, start_time: datetime = None) -> Match:
        with self.SessionLocal() as db:
            match = db.query(Match).filter(Match.url == url).first()
            if not match:
                return self.create_match(event_name=event_name, team_names=team_names, url=url, format=format,
                                  ongoing=ongoing, start_time=start_time)

            match.teams.clear()
            if team_names:
                teams = db.query(Team).filter(Team.name.in_(team_names)).all()
                match.teams.extend(teams)
            match.format = format
            match.ongoing = ongoing
            match.start_time = start_time
            db.commit()
            db.refresh(match)
            return match

    def get_matches_for_user(self, user_id: int) -> dict:
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []

            event_matches = db.query(Match).options(
                joinedload(Match.event),
                joinedload(Match.teams)
            ).join(Event).join(
                UserEventSubscription,
                UserEventSubscription.event_id == Event.id
            ).filter(UserEventSubscription.user_id == user_id).all()

            team_matches = db.query(Match).options(
                joinedload(Match.event),
                joinedload(Match.teams)
            ).join(match_team_association).join(
                Team
            ).join(
                UserTeamSubscription,
                UserTeamSubscription.team_id == Team.id
            ).filter(UserTeamSubscription.user_id == user_id).all()

            return event_matches + team_matches

    def subscribe_user_to_event(self, user_id: int, event_id: int) -> str:
        with self.SessionLocal() as db:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return ''
            if db.query(UserEventSubscription).filter_by(
                    user_id=user_id, event_id=event.id
            ).first():
                return event.name

            subscription = UserEventSubscription(user_id=user_id, event_id=event.id)
            db.add(subscription)
            db.commit()
            return event.name

    def subscribe_user_to_team(self, user_id: int, team_id: int) -> str:
        with self.SessionLocal() as db:
            team = db.query(Team).filter(Team.id == team_id).first()
            if not team:
                return ''

            if db.query(UserTeamSubscription).filter_by(
                    user_id=user_id, team_id=team.id
            ).first():
                return team.name

            subscription = UserTeamSubscription(user_id=user_id, team_id=team.id)
            db.add(subscription)
            db.commit()
            return team.name

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

    def get_all_events(self) -> list[Event]:
        with self.SessionLocal() as db:
            return db.query(Event).all()

    def get_all_teams(self) -> list[Team]:
        with self.SessionLocal() as db:
            return db.query(Team).all()

    def get_user_subscribed_events(self, user_id: int) -> list[Event]:
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
            return user.subscribed_events

    def get_user_subscribed_teams(self, user_id: int) -> list[Team]:
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
            return user.subscribed_teams

    def delete_ended_events(self) -> int:
        with self.SessionLocal() as db:
            current_time = datetime.now(timezone.utc) - timedelta(days=1)
            deleted_count = db.query(Event).filter(Event.end_date < current_time).delete()
            db.commit()
            return deleted_count

    def delete_matches_not_in_list(self, url_list: list[str]) -> int:
        with self.SessionLocal() as db:
            if not url_list:
                return 0

            deleted_count = db.query(Match).filter(~Match.url.in_(url_list)).delete()
            db.commit()
            return deleted_count

    def get_users_subscribed_to_match(self, match_url: int) -> list[User]:
        with self.SessionLocal() as db:
            match = db.query(Match).options(
                joinedload(Match.teams),
                joinedload(Match.event)
            ).filter(Match.url == match_url).first()

            if not match:
                return []

            team_ids = [team.id for team in match.teams]

            users = db.query(User).distinct().filter(
                (User.id.in_(
                    db.query(UserEventSubscription.user_id)
                    .filter(UserEventSubscription.event_id == match.event_id)
                )) |
                (User.id.in_(
                    db.query(UserTeamSubscription.user_id)
                    .filter(UserTeamSubscription.team_id.in_(team_ids))
                ))
            ).all()

            return users

    def get_ongoing_matches(self):
        with self.SessionLocal() as db:
            return db.query(Match).options(
                joinedload(Match.teams),
                joinedload(Match.event)
            ).filter(Match.ongoing == True).all()

    def add_stream_to_match(self, match_url: str, stream_link: str, stream_name: str) -> Stream:
        with self.SessionLocal() as db:
            match = db.query(Match).filter(Match.url == match_url, Match.ongoing == True).first()
            if not match:
                return None

            existing_stream = db.query(Stream).filter(Stream.link == stream_link).first()
            if existing_stream:
                return None

            stream = Stream(link=stream_link, match_id=match.id, name=stream_name)
            db.add(stream)
            db.commit()
            db.refresh(stream)
            return stream

    def get_streams_for_match(self, match_url: str) -> list[Stream]:
        with self.SessionLocal() as db:
            match = db.query(Match).filter(Match.url == match_url).first()
            if not match:
                return []
            return match.streams

    def set_notifed_match(self, match_url: str):
        with self.SessionLocal() as db:
            match = db.query(Match).filter(Match.url == match_url).first()
            match.notified = True
            db.commit()
            db.refresh(match)

    def check_user_is_admin(self, user_id: int) -> bool:
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            return user.is_admin

    def set_admin(self, user_id: int):
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            user.is_admin = True
            db.commit()
            db.refresh(user)

    def set_timezone(self, user_id: int, time_zone: int) -> bool:
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if -12 <= time_zone <= 14:
                user.time_zone = time_zone
                db.commit()
                db.refresh(user)
                return True
            return False

    def get_timezone(self, user_id: int) -> int:
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user.time_zone:
                self.set_timezone(user_id, 0)
            return user.time_zone