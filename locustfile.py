from locust import HttpUser, between, task

user_int = 0
emails = []
passwords = []
for i in range(100):
    emails.append(i)
    passwords.append(i)

print(emails)
print(passwords)

class HelloWorldUser(HttpUser):
    wait_time = between(1,3)

    def on_start(self):
        global user_int
        response = self.client.post(
            "login",
            json = {
                "email": str(emails[user_int]),
                "password": str(passwords[user_int])
            }
        )
        print(f"user logged in: {user_int}")
        if response.status_code != 200:
            raise Exception(f"login failed: {response.text}")  # noqa: TRY002
        user_int += 1

    @task
    def get_history(self):
        self.client.get("get_webpage_history")

    @task 
    def get_data(self):
        self.client.post(
            "get_data",
            json = {"action": "get_role"}
            )

    @task
    def planning_agent(self):
        self.client.get("planning_agent")