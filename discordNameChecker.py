# :\\__ Discordize - Discord Name Generator & Checker
# :\\__ Viperize - MIT License
#----------------------------------------------
# | Version
#----------------------------------------------
__version__ = 0.1

# | Imports
#----------------------------------------------
import requests
import string
import json
from time import sleep
from random import choice
from colorama import Fore, init
from datetime import datetime

init(autoreset=True)

# | Constants
#----------------------------------------------
URL = "https://discord.com/api/v10/users/@me"
DELAY = 2

# | Variables
#----------------------------------------------
token = "PUT YOUR TOKEN INTO THE FILE TOKEN.TXT, NOT HERE"
headers = {}

# | Main Class
#----------------------------------------------
class UsernameChecker:


    def __init__(self, webhook=None, debugging=False):
        self.validUsernames = []
        self.webhook = webhook
        self.debugging = debugging
        self.timeStarted = datetime.now()

    def check_username(self, username):
        data = {"username": username}

        while True:
            try:
                r = requests.patch(URL, headers=headers, data=json.dumps(data))
                rJson = r.json()

                # If rate limited, retry
                if r.status_code == 429:
                    retryTime = max(rJson.get("retry_after", 5), 5)
                    print(Fore.RED + f"Rate limited! Resuming in {retryTime}s")
                    sleep(retryTime)
                    continue

                errors = rJson.get("errors")
                if errors:
                    if errors.get("username"):
                        # Username taken/invalid
                        if self.debugging:
                            print(Fore.RED + username)
                    else:
                        # Username available
                        print(Fore.GREEN + username)
                        self.validUsernames.append(username)
                        with open("validUsernames.txt", "a") as f:
                            f.write(f"{username}\n")
                        if self.webhook:
                            self.send_to_discord(username)
                else:
                    print(Fore.RED + f'Error validating >> {rJson.get("message")}')
                break

            except Exception as e:
                print(Fore.RED + f"Username check errored: {e}")
                break

    def from_text_list(self, file="./checkUsernames.txt"):
        with open(file, "r") as f:
            for name in f:
                sleep(DELAY)
                self.check_username(name.strip())

        self.is_completed()

    def generate_and_check(self, char_lengths=[3, 4]):
        characters = string.ascii_lowercase + string.digits
        letters = set(string.ascii_lowercase)
        checked = set()

        print(Fore.LIGHTYELLOW_EX + f"\nGenerating {'/'.join(map(str, char_lengths))}-char usernames...")
        print(Fore.LIGHTYELLOW_EX + "Press Ctrl+C to stop\n")

        try:
            while True:
                length = choice(char_lengths)
                while True:
                    username = ''.join(choice(characters) for _ in range(length))
                    if any(c in letters for c in username) and username not in checked:
                        break
                checked.add(username)
                sleep(DELAY)
                self.check_username(username)
        except KeyboardInterrupt:
            print(Fore.LIGHTYELLOW_EX + f"\n\nStopped. Checked {len(checked)} usernames.")
            self.is_completed()

    def send_to_discord(self, name):
        data = {
            "content": f"`{name}` is available",
        }
        try:
            requests.post(self.webhook, json=data)
        except Exception as e:
            print(Fore.RED + f"Error sending data to webhook: {e}")

    def is_completed(self):
        print(f"\nCompleted in {round((datetime.now()-self.timeStarted).seconds)} seconds")
        print(f"{Fore.LIGHTYELLOW_EX}Available Names: {', '.join(self.validUsernames)}")

# | Functions
#----------------------------------------------
def check_if_outdated():
    cv = requests.get("https://raw.githubusercontent.com/ozo77/discord-user-gen/main/currentVersion.txt").text.strip()
    if cv != str(__version__):
        print(Fore.RED + "[!] THIS VERSION IS OUTDATED, PLEASE UPDATE")

def check_token():
    global token, headers
    
    with open("./token.txt", "r") as f:
        token = f.read().strip()

    headers = {
        "Content-Type": "application/json",
        "Authorization": token,
    }

    discordUser = requests.get(URL, headers=headers)
    if discordUser.status_code == 401:
        print(Fore.RED + "Invalid token inside the file token.txt")
        exit()

    return discordUser.json().get("username")

def show_options():
    discordName = check_token()
    print(Fore.LIGHTYELLOW_EX +
f"""
=============================================================================

██████╗ ██╗███████╗ ██████╗ ██████╗ ██████╗ ██████╗ ██╗███████╗███████╗
██╔══██╗██║██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗██║╚══███╔╝██╔════╝
██║  ██║██║███████╗██║     ██║   ██║██████╔╝██║  ██║██║  ███╔╝ █████╗  
██║  ██║██║╚════██║██║     ██║   ██║██╔══██╗██║  ██║██║ ███╔╝  ██╔══╝  
██████╔╝██║███████║╚██████╗╚██████╔╝██║  ██║██████╔╝██║███████╗███████╗
╚═════╝ ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═╝╚══════╝╚══════╝
                                                                    
>> >> ozo77 (https://github.com/ozo77)
>> >> v0.1
>> >> {discordName}
{Fore.WHITE}
> 1 ) Generate & check 3-char usernames (infinite)
> 2 ) Generate & check 4-char usernames (infinite)
> 3 ) Generate & check 3 & 4-char usernames (infinite)
> 4 ) Check from username list
{Fore.LIGHTYELLOW_EX}
=============================================================================

""")

# | Initialise
#----------------------------------------------
if __name__ == "__main__":
    check_if_outdated()

    while True:
        show_options()

        try:
            d_webhook = None
            debugging = False
            operation = input(">> ")

            if operation not in ["1", "2", "3", "4"]:
                raise Exception("Invalid input")

            discord = input("Use a webhook? (y/n) ")
            if discord.lower() not in ["y", "n"]:
                raise Exception("Invalid webhook option")
            if discord.lower() == "y":
                with open("./discordWebhook.txt", "r") as f:
                    try:
                        f_url = f.read().strip()
                        wr = requests.get(f_url).json()
                        if wr.get("token"):
                            d_webhook = f_url
                        else:
                            raise Exception("Invalid discord webhook")
                    except Exception as e:
                        print(Fore.RED + f"Error with webhook: {e}")

            debugging_prompt = input("Display unsuccessful names? (y/n) ")
            if debugging_prompt.lower() not in ["y", "n"]:
                raise Exception("Invalid input")
            if debugging_prompt.lower() == "y":
                debugging = True

            checkerInstance = UsernameChecker(d_webhook, debugging)

            if operation == "1":
                checkerInstance.generate_and_check([3])
            elif operation == "2":
                checkerInstance.generate_and_check([4])
            elif operation == "3":
                checkerInstance.generate_and_check([3, 4])
            elif operation == "4":
                checkerInstance.from_text_list()

            sleep(5)

        except Exception as e:
            print(Fore.RED + f"Error: {e}\n\n")
            sleep(1)
