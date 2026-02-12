import random
import csv
import unittest
import asyncio
from validator import EmailValidator
from database import Database

def generate_mock_csv(filename, count=1000):
    domains = ["gmail.com", "yahoo.com", "outlook.com", "mailinator.com", "nonexistent-xyz-123.com"]
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        for i in range(count):
            user = f"user_{i}_{random.randint(1000, 9999)}"
            domain = random.choice(domains)
            writer.writerow([f"{user}@{domain}"])

class TestEmailSaaS(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.validator = EmailValidator(self.db)
        self.db.create_or_update_user("admin@rocket.com", "Admin", "", "admin")
        self.user = self.db.get_user_by_email("admin@rocket.com")

    def test_user_logging(self):
        self.db.log_verification(self.user[0], "test@mail.com", "Valid", "SMTP OK")
        logs = self.db.get_user_logs(self.user[0])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0][0], "test@mail.com")

    def test_limit_logic(self):
        # 4k limit test
        self.db.update_user_credits(self.user[0], 4000)
        updated = self.db.get_user_by_email("admin@rocket.com")
        self.assertEqual(updated[6], 4000)
        # Verify it logic in app.py would block this, but here we just verify the state

if __name__ == "__main__":
    unittest.main()
