from helpers import get_filtered_elements
import time
from bs4 import BeautifulSoup


class ActionAgent:
    """
    Contains all the basic methods use to interact with the browser.
    """

    def __init__(self, page) -> None:
        self.page = page
        self.goal_achieved = False

    def _google_search(self, text):
        self.page.goto("https://www.google.com")
        elements = get_filtered_elements(self.page)
        for element in elements:
            if "search" == str(element["ariaLabel"]).lower():
                # self.page.locator(f"xpath={element['path']}").type(f"{text}\n")
                self._type(element["path"], text)
                break

    def _go_to_url(self, url):
        self.page.goto(url)

    def _click(self, xpath):
        self.page.locator(f"xpath={xpath}").click()

    def _type(self, xpath, text):
        # clear that field first
        self.page.locator(f"xpath={xpath}").fill("")
        self.page.locator(f"xpath={xpath}").type(f"{text}\n")

    def _scroll_up(self):
        self.page.evaluate("()=>{window.scrollBy(0, -window.innerHeight+200)}")

    def _scroll_down(self):
        self.page.evaluate("()=>{window.scrollBy(0, window.innerHeight-200)}")

    def _wait(self, sec=None):
        time.sleep(sec if sec else 2)

    def _go_back(self):
        self.page.go_back()

    def _set_goal_achieved(self):
        self.goal_achieved = True
        

    def get_goal_achieved(self):
        return self.goal_achieved

    def execute(self, action, *args):
        print(f"\n\nEXECUTING: self.{action}(*{args})\n\n")
        exec(f"self.{action}(*{args})")

    def wait_till_idle(self):
        self.page.wait_for_load_state("domcontentloaded")


