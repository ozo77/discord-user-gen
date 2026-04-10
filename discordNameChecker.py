# :\\__ Discordize - Discord Name Generator & Checker
# :\\__ ozo77 - MIT License
#----------------------------------------------
# | Version
#----------------------------------------------
__version__ = 0.3

# | Imports
#----------------------------------------------
import requests
import string
import json
import threading
import os
from time import sleep, time
from random import choice, shuffle
from colorama import Fore, init
from datetime import datetime

init(autoreset=True)

# | Constants
#----------------------------------------------
URL = "https://discord.com/api/v10/users/@me"
CHECK_URL = "https://discord.com/api/v10/unique-username/username-attempt-unauthed"
CHECK_HEADERS = {"Content-Type": "application/json"}
PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
]

# | Variables
#----------------------------------------------
token = ""
headers = {}
proxy_list = []
working_proxies = []
proxy_lock = threading.Lock()
print_lock = threading.Lock()
file_lock = threading.Lock()
stats = {"checked": 0, "available": 0, "errors": 0, "rate_limited": 0, "start": 0}

# | Proxy Functions
#----------------------------------------------
def scrape_proxies():
    proxies = set()
    for url in PROXY_SOURCES:
        try:
            r = requests.get(url, timeout=10)
            for line in r.text.strip().splitlines():
                line = line.strip()
                if ":" in line and len(line) < 30:
                    parts = line.split(":")
                    if len(parts) == 2 and parts[1].isdigit():
                        proxies.add(line)
        except Exception:
            pass
    return list(proxies)

def load_proxies():
    global proxy_list
    try:
        with open("proxies.txt", "r") as f:
            file_proxies = [p.strip() for p in f.readlines() if p.strip()]
            if file_proxies:
                proxy_list = file_proxies
                print(Fore.GREEN + f"  Loaded {len(proxy_list)} proxies from proxies.txt")
                return
    except FileNotFoundError:
        pass
    print(Fore.LIGHTYELLOW_EX + "  Scraping free proxies...")
    proxy_list = scrape_proxies()
    if proxy_list:
        shuffle(proxy_list)
        with open("proxies.txt", "w") as f:
            f.write("\n".join(proxy_list))
        print(Fore.GREEN + f"  Scraped {len(proxy_list)} proxies")
    else:
        print(Fore.RED + "  No proxies found")

def validate_proxies(max_test=200):
    global working_proxies
    working_proxies = []
    test_data = json.dumps({"username": "test"})
    to_test = proxy_list[:max_test]
    print(Fore.LIGHTYELLOW_EX + f"  Testing {len(to_test)} proxies...")

    tested = 0
    batch_size = 20
    lock = threading.Lock()

    def test_proxy(p):
        nonlocal tested
        px = {"http": f"http://{p}", "https": f"http://{p}"}
        try:
            r = requests.post(CHECK_URL, headers=CHECK_HEADERS, data=test_data, proxies=px, timeout=6)
            if r.status_code in (200, 429):
                with lock:
                    working_proxies.append(p)
        except Exception:
            pass
        with lock:
            tested += 1
            if tested % 50 == 0:
                print(Fore.CYAN + f"  Tested {tested}/{len(to_test)} | Working: {len(working_proxies)}")

    for i in range(0, len(to_test), batch_size):
        batch = to_test[i:i+batch_size]
        threads = []
        for p in batch:
            t = threading.Thread(target=test_proxy, args=(p,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=10)

    print(Fore.GREEN + f"  Found {len(working_proxies)} working proxies out of {len(to_test)} tested")
    return working_proxies

def get_proxy():
    with proxy_lock:
        if not working_proxies:
            return None
        proxy = choice(working_proxies)
    return proxy, {"http": f"http://{proxy}", "https": f"http://{proxy}"}

def remove_proxy(proxy_str):
    with proxy_lock:
        try:
            working_proxies.remove(proxy_str)
        except ValueError:
            pass

# | Progress Functions
#----------------------------------------------
def load_checked():
    checked = set()
    if os.path.exists("checked.txt"):
        with open("checked.txt", "r") as f:
            for line in f:
                checked.add(line.strip())
    return checked

def save_checked(username):
    with file_lock:
        with open("checked.txt", "a") as f:
            f.write(f"{username}\n")

# | Main Class
#----------------------------------------------
class UsernameChecker:

    def __init__(self, webhook=None, debugging=False, use_proxies=False):
        self.validUsernames = []
        self.webhook = webhook
        self.debugging = debugging
        self.use_proxies = use_proxies
        self.timeStarted = datetime.now()
        self.running = True
        self.paused = False
        self.pause_until = 0

    def check_username_direct(self, username):
        data = json.dumps({"username": username})
        try:
            r = requests.post(CHECK_URL, headers=CHECK_HEADERS, data=data, timeout=10)
            rJson = r.json()

            if r.status_code == 429:
                retry = rJson.get("retry_after", 60)
                stats["rate_limited"] += 1
                with print_lock:
                    print(Fore.LIGHTYELLOW_EX + f"  Rate limited! Waiting {int(retry)}s...")
                self.pause_until = time() + retry
                self.paused = True
                return "rate_limited"

            if r.status_code == 200:
                stats["checked"] += 1
                save_checked(username)
                if rJson.get("taken") is False:
                    stats["available"] += 1
                    with print_lock:
                        print(Fore.GREEN + f"  + {username} is available!")
                    with file_lock:
                        self.validUsernames.append(username)
                        with open("validUsernames.txt", "a") as f:
                            f.write(f"{username}\n")
                    if self.webhook:
                        self.send_to_discord(username)
                else:
                    if self.debugging:
                        with print_lock:
                            print(Fore.RED + f"  - {username}")
                return "ok"
            return "error"
        except Exception:
            stats["errors"] += 1
            return "error"

    def check_username_proxy(self, username):
        data = json.dumps({"username": username})
        for attempt in range(3):
            result = get_proxy()
            if not result:
                return self.check_username_direct(username)
            proxy_str, proxy_dict = result
            try:
                r = requests.post(CHECK_URL, headers=CHECK_HEADERS, data=data, proxies=proxy_dict, timeout=8)
                rJson = r.json()
                if r.status_code == 429:
                    remove_proxy(proxy_str)
                    continue
                if r.status_code == 200:
                    stats["checked"] += 1
                    save_checked(username)
                    if rJson.get("taken") is False:
                        stats["available"] += 1
                        with print_lock:
                            print(Fore.GREEN + f"  + {username} is available!")
                        with file_lock:
                            self.validUsernames.append(username)
                            with open("validUsernames.txt", "a") as f:
                                f.write(f"{username}\n")
                        if self.webhook:
                            self.send_to_discord(username)
                    else:
                        if self.debugging:
                            with print_lock:
                                print(Fore.RED + f"  - {username}")
                    return "ok"
                else:
                    remove_proxy(proxy_str)
                    continue
            except (requests.exceptions.ProxyError,
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ReadTimeout):
                remove_proxy(proxy_str)
                continue
            except Exception:
                stats["errors"] += 1
                continue
        return "error"

    def generate_and_check(self, char_lengths):
        characters = string.ascii_lowercase + string.digits
        letters = set(string.ascii_lowercase)
        checked = load_checked()
        delay = 2.0

        lens = '/'.join(map(str, char_lengths))
        mode = "PROXY" if self.use_proxies else "DIRECT"
        print(Fore.LIGHTYELLOW_EX + f"\n  Generating {lens}-char usernames [{mode} mode]")
        if not self.use_proxies:
            print(Fore.LIGHTYELLOW_EX + f"  Delay: {delay}s between checks")
            print(Fore.LIGHTYELLOW_EX + f"  Will auto-pause on rate limit and resume after cooldown")
        else:
            print(Fore.LIGHTYELLOW_EX + f"  Working proxies: {len(working_proxies)}")
        print(Fore.LIGHTYELLOW_EX + f"  Already checked: {len(checked)} (skipping)")
        print(Fore.LIGHTYELLOW_EX + "  Press Ctrl+C to stop\n")

        stats["start"] = time()
        stats["checked"] = 0
        stats["available"] = 0
        stats["errors"] = 0
        stats["rate_limited"] = 0

        if self.use_proxies and working_proxies:
            self._run_proxy_mode(char_lengths, characters, letters, checked)
        else:
            self._run_direct_mode(char_lengths, characters, letters, checked, delay)

    def _run_direct_mode(self, char_lengths, characters, letters, checked, delay):
        try:
            while self.running:
                if self.paused:
                    wait = self.pause_until - time()
                    if wait > 0:
                        mins = int(wait // 60)
                        secs = int(wait % 60)
                        with print_lock:
                            print(Fore.LIGHTYELLOW_EX + f"\r  Paused - resuming in {mins}m {secs}s | Checked: {stats['checked']} | Available: {stats['available']}    ", end="", flush=True)
                        sleep(min(wait, 10))
                        continue
                    else:
                        self.paused = False
                        print(Fore.GREEN + "\n  Resuming checks...")

                length = choice(char_lengths)
                while True:
                    username = ''.join(choice(characters) for _ in range(length))
                    if any(c in letters for c in username) and username not in checked:
                        checked.add(username)
                        break

                result = self.check_username_direct(username)

                if result == "ok" and stats["checked"] % 10 == 0:
                    elapsed = time() - stats["start"]
                    rate = stats["checked"] / elapsed if elapsed > 0 else 0
                    print(Fore.CYAN + f"  [Stats] Checked: {stats['checked']} | Available: {stats['available']} | Rate: {rate:.2f}/s | Errors: {stats['errors']}")

                if result != "rate_limited":
                    sleep(delay)

        except KeyboardInterrupt:
            self.running = False
            print(Fore.LIGHTYELLOW_EX + "\n\n  Stopping...")
            self.is_completed()

    def _run_proxy_mode(self, char_lengths, characters, letters, checked):
        import queue
        thread_count = min(len(working_proxies), 50)
        username_queue = queue.Queue(maxsize=thread_count * 2)
        checked_lock = threading.Lock()

        def worker():
            while self.running:
                try:
                    username = username_queue.get(timeout=2)
                    self.check_username_proxy(username)
                    username_queue.task_done()
                except queue.Empty:
                    continue

        def status_printer():
            while self.running:
                sleep(10)
                elapsed = time() - stats["start"]
                rate = stats["checked"] / elapsed if elapsed > 0 else 0
                with print_lock:
                    print(Fore.CYAN + f"\n  [Stats] Checked: {stats['checked']} | Available: {stats['available']} | Rate: {rate:.1f}/s | Proxies: {len(working_proxies)} | Threads: {thread_count}\n")

        workers = []
        for _ in range(thread_count):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            workers.append(t)

        status_thread = threading.Thread(target=status_printer, daemon=True)
        status_thread.start()

        try:
            while self.running:
                length = choice(char_lengths)
                with checked_lock:
                    while True:
                        username = ''.join(choice(characters) for _ in range(length))
                        if any(c in letters for c in username) and username not in checked:
                            checked.add(username)
                            break
                username_queue.put(username)
                if not working_proxies:
                    print(Fore.RED + "\n  All proxies dead! Switching to direct mode...")
                    self.use_proxies = False
                    self._run_direct_mode(char_lengths, string.ascii_lowercase + string.digits, set(string.ascii_lowercase), checked, 2.0)
                    return
        except KeyboardInterrupt:
            self.running = False
            print(Fore.LIGHTYELLOW_EX + "\n\n  Stopping threads...")
            self.is_completed()

    def from_text_list(self, file="./checkUsernames.txt"):
        with open(file, "r") as f:
            names = [n.strip() for n in f.readlines() if n.strip()]
        checked = load_checked()
        names = [n for n in names if n not in checked]
        if not names:
            print(Fore.GREEN + "\n  All names in the list have already been checked!")
            return
        print(Fore.LIGHTYELLOW_EX + f"\n  Checking {len(names)} usernames...")
        stats["start"] = time()
        stats["checked"] = 0
        stats["available"] = 0
        stats["errors"] = 0
        stats["rate_limited"] = 0

        if self.use_proxies and working_proxies:
            import queue
            username_queue = queue.Queue()
            for name in names:
                username_queue.put(name)
            tc = min(len(working_proxies), 50)
            def worker():
                while not username_queue.empty():
                    try:
                        username = username_queue.get(timeout=1)
                        self.check_username_proxy(username)
                        username_queue.task_done()
                    except queue.Empty:
                        break
            workers = []
            for _ in range(tc):
                t = threading.Thread(target=worker, daemon=True)
                t.start()
                workers.append(t)
            for t in workers:
                t.join()
        else:
            try:
                for i, name in enumerate(names):
                    if self.paused:
                        wait = self.pause_until - time()
                        if wait > 0:
                            mins = int(wait // 60)
                            secs = int(wait % 60)
                            print(Fore.LIGHTYELLOW_EX + f"\r  Paused - resuming in {mins}m {secs}s | {i}/{len(names)}    ", end="", flush=True)
                            sleep(min(wait, 10))
                            continue
                        else:
                            self.paused = False
                            print(Fore.GREEN + "\n  Resuming...")
                    result = self.check_username_direct(name)
                    if result == "ok" and stats["checked"] % 10 == 0:
                        print(Fore.CYAN + f"  [{i+1}/{len(names)}] Checked: {stats['checked']} | Available: {stats['available']}")
                    if result != "rate_limited":
                        sleep(2.0)
            except KeyboardInterrupt:
                pass

        self.is_completed()

    def send_to_discord(self, name):
        data = {"content": f"`{name}` is available"}
        try:
            requests.post(self.webhook, json=data, timeout=5)
        except Exception:
            pass

    def is_completed(self):
        elapsed = time() - stats["start"] if stats["start"] else 0
        print(f"\n  Completed in {elapsed:.0f} seconds")
        print(f"  {Fore.LIGHTYELLOW_EX}Checked: {stats['checked']} | Available: {stats['available']} | Rate Limited: {stats['rate_limited']}x")
        if self.validUsernames:
            print(f"  {Fore.GREEN}Available Names: {', '.join(self.validUsernames)}")
        print(f"  {Fore.CYAN}Results saved to validUsernames.txt")

# | Functions
#----------------------------------------------
def check_token():
    global token, headers
    with open("./token.txt", "r") as f:
        token = f.read().strip().splitlines()[0].strip()
    headers = {"Content-Type": "application/json", "Authorization": token}
    discordUser = requests.get(URL, headers=headers)
    if discordUser.status_code == 401:
        print(Fore.RED + "  Invalid token inside the file token.txt")
        exit()
    return discordUser.json().get("username")

def show_options():
    discordName = check_token()
    proxy_status = f"{len(working_proxies)} working" if working_proxies else f"{len(proxy_list)} scraped (not tested)"
    print(Fore.LIGHTYELLOW_EX + f"""
=============================================================================

 ██████╗ ██╗███████╗ ██████╗ ██████╗ ██████╗ ██████╗ ██╗███████╗███████╗
 ██╔══██╗██║██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗██║╚══███╔╝██╔════╝
 ██║  ██║██║███████╗██║     ██║   ██║██████╔╝██║  ██║██║  ███╔╝ █████╗
 ██║  ██║██║╚════██║██║     ██║   ██║██╔══██╗██║  ██║██║ ███╔╝  ██╔══╝
 ██████╔╝██║███████║╚██████╗╚██████╔╝██║  ██║██████╔╝██║███████╗███████╗
 ╚═════╝ ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═╝╚══════╝╚══════╝

  >> ozo77 (https://github.com/ozo77)
  >> v{__version__}
  >> {discordName}
  >> Proxies: {proxy_status}
{Fore.WHITE}
  1 ) Generate & check 3-char usernames
  2 ) Generate & check 4-char usernames
  3 ) Generate & check 3 & 4-char usernames
  4 ) Check from username list
  5 ) Scrape & test proxies
{Fore.LIGHTYELLOW_EX}
=============================================================================

""")

# | Initialise
#----------------------------------------------
if __name__ == "__main__":
    load_proxies()

    while True:
        show_options()

        try:
            d_webhook = None
            debugging = False
            use_proxies = False
            operation = input("  >> ")

            if operation == "5":
                print()
                proxy_list.clear()
                working_proxies.clear()
                proxy_list.extend(scrape_proxies())
                shuffle(proxy_list)
                if proxy_list:
                    with open("proxies.txt", "w") as f:
                        f.write("\n".join(proxy_list))
                    print(Fore.GREEN + f"  Scraped {len(proxy_list)} proxies")
                    validate_proxies()
                else:
                    print(Fore.RED + "  No proxies found")
                input("\n  Press Enter to continue...")
                continue

            if operation not in ["1", "2", "3", "4"]:
                raise Exception("Invalid input")

            discord = input("  Use a webhook? (y/n) ")
            if discord.lower() == "y":
                with open("./discordWebhook.txt", "r") as f:
                    try:
                        f_url = f.read().strip()
                        wr = requests.get(f_url).json()
                        if wr.get("token"):
                            d_webhook = f_url
                            print(Fore.GREEN + f"  Webhook connected: {wr.get('name', 'Unknown')}")
                        else:
                            print(Fore.RED + "  Invalid discord webhook")
                    except Exception as e:
                        print(Fore.RED + f"  Webhook error: {e}")

            debugging_prompt = input("  Display unsuccessful names? (y/n) ")
            if debugging_prompt.lower() == "y":
                debugging = True

            if working_proxies:
                proxy_prompt = input(f"  Use proxies? ({len(working_proxies)} working) (y/n) ")
                if proxy_prompt.lower() == "y":
                    use_proxies = True
            elif proxy_list:
                proxy_prompt = input(f"  Test & use proxies? ({len(proxy_list)} scraped) (y/n) ")
                if proxy_prompt.lower() == "y":
                    validate_proxies()
                    if working_proxies:
                        use_proxies = True
                    else:
                        print(Fore.RED + "  No working proxies found, using direct mode")

            if not use_proxies:
                print(Fore.CYAN + "\n  Direct mode: ~14 checks per batch, auto-pauses on rate limit")
                print(Fore.CYAN + "  For faster checking, use proxies (option 5 to scrape & test)\n")

            checkerInstance = UsernameChecker(d_webhook, debugging, use_proxies)

            if operation == "1":
                checkerInstance.generate_and_check([3])
            elif operation == "2":
                checkerInstance.generate_and_check([4])
            elif operation == "3":
                checkerInstance.generate_and_check([3, 4])
            elif operation == "4":
                checkerInstance.from_text_list()

            sleep(3)

        except KeyboardInterrupt:
            print(Fore.LIGHTYELLOW_EX + "\n\n  Returning to menu...")
            sleep(1)
        except Exception as e:
            print(Fore.RED + f"  Error: {e}\n")
            sleep(1)
