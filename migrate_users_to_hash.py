"""One-time script to hash any plaintext passwords for existing users."""

from db import Session, User
from werkzeug.security import generate_password_hash


def needs_hash(pw: str) -> bool:
    """Detect if the stored password looks unhashed.

    Werkzeug hashes typically include a '$' separator.
    """
    return "$" not in pw


def main() -> None:
    db = Session()
    users = db.query(User).all()
    for user in users:
        if needs_hash(user.password_hash):
            user.password_hash = generate_password_hash(user.password_hash)
            print(f"Updated password for {user.email}")
    db.commit()
    db.close()


if __name__ == "__main__":
    main()

