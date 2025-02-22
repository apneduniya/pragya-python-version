"""PlaywrightAgent abstraction, which inherits from AgenticGPT."""
import time
import json
import logging
from agentic_gpt.agent import AgenticGPT
from bs4 import Tag
import playwright
from playwright.sync_api import sync_playwright
from typing import Dict
from inspect import signature
from typing import Callable


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Action:
    """Action class takes a name, a description, a function that it executes.

    A well-defined action will return a textual description of the state
    of the world so that the agent can understand what to do next."""

    def __init__(self, name: str, description: str, function: Callable):
        self.name = name
        self.description = description
        self.function = function

    def to_string(self):
        """Return a string representation of the action, including the
        function signature."""
        func_signature = ", ".join(
            [str(param) for param in signature(self.function).parameters.values()]
        )
        return (
            f"`{self.name}`, called with params ({func_signature}): {self.description}"
        )

    def execute(self, *args):
        """Execute the action with the given arguments."""
        return self.function(*args)


def get_current_browser_view_from_mapping(mapping):
    """Get what the AI sees."""
    elements = "\n".join(
        [
            "element id #{id}: {html_string}".format(
                id=i + 1, html_string=mapping[key]["transformed"]
            )
            for i, key in enumerate(mapping.keys())
        ]
    )
    return elements


def get_tag_name(locator):
    """Get the tag name from a locator."""
    return locator.evaluate("(element) => element.tagName").lower()


def wait(seconds):
    """Wait for `seconds` seconds."""
    time.sleep(seconds)


def get_outer_html(locator):
    """Get the outer HTML from a locator."""
    return locator.evaluate("(element) => element.outerHTML")


class PlaywrightAgent(AgenticGPT):
    def __init__(
        self,
        playwright_obj,
        objective,
        headless=False,
        cookies="",
        actions_available=[],
        model="gpt-4",
        max_steps=100,
        verbose=False,
    ):
        """Initialize a Playwright agent. The correct way is to do:

        ```
        with sync_playwright() as playwright:
            agent = PlaywrightAgent(playwright, objective, actions_available)
        ```

        as this ensures that the Playwright cleanup is done correctly when
        the agent is done.
        """
        # Instantiate the browser and page.
        self.playwright = playwright_obj
        self.headless = headless
        self.browser = playwright_obj.chromium.launch(headless=headless)
        self.browser_context = self.browser.new_context()
        self.cookies = cookies
        self.page = self.browser_context.new_page()

        if self.cookies:
            if isinstance(self.cookies, str):
                with open(self.cookies, "r") as f:
                    self.cookies = json.loads(f.read())

            self.browser_context.add_cookies(self.cookies)

        # To be set by __preprocess_html_for_prompt.
        self._current_browser_mapping = None

        # Instantiate the action set.
        all_actions = []
        all_actions.extend(
            [
                Action(
                    name="go_to_page",
                    description="Navigate the page to a url.",
                    function=self.__go_to_page,
                ),
                Action(
                    name="click_element",
                    description="Click an element with id `element_id_num`.",
                    function=self.__click_element,
                ),
                Action(
                    name="type_into_element",
                    description="Type into an element with id `element_id_num`.",
                    function=self.__type_into_element,
                ),
                Action(
                    name="type_and_submit_into_element",
                    description="Type into an element with id `element_id_num` and submit.",
                    function=self.__type_and_submit_into_element,
                ),
                Action(
                    name="wait",
                    description="Wait for `seconds` seconds.",
                    function=wait,
                ),
            ]
        )
        all_actions.extend(actions_available)

        super().__init__(
            objective,
            actions_available=all_actions,
            model=model,
            max_steps=max_steps,
            verbose=verbose,
        )

    def __get_context(self):
        """Get the context for the AI to read."""
        context = "The format of the browser content is highly simplified; all formatting elements are stripped.\n"
        context += "When choosing elements, please use the `id` number.\n\n"
        context += self.__preprocess_html_for_prompt()
        return context
  
    def __get_object_from_mapping(self, element_id_num: int):
        """Get the object from the mapping."""
        if isinstance(element_id_num, str):
            element_id_num = int(element_id_num)
        return self._current_browser_mapping[element_id_num]["object"]

    def __click_element(self, element_id_num: int):
        """Click an element with id `element_id_num`."""
        try:
            element_object = self.__get_object_from_mapping(element_id_num)
            element_object.click()
            time.sleep(2)
            context = self.__get_context()
            return {"context": context}
        except playwright._impl._api_types.Error as exc:
            raise exc

    def __type_into_element(self, element_id_num: int, text: str):
        """Type into an element with id `element_id_num`."""
        try:
            element_object = self.__get_object_from_mapping(element_id_num)
            element_object.fill(text)
            context = self.__get_context()
            return {"context": context}
        except playwright._impl._api_types.Error as exc:
            raise exc

    def __type_and_submit_into_element(self, element_id_num: int, text: str):
        """Type into an element with id `element_id_num` and submit."""
        try:
            element_object = self.__get_object_from_mapping(element_id_num)
            element_object.fill(text)
            element_object.press("Enter")
            time.sleep(2)
            context = self.__get_context()
            return {"context": context}
        except playwright._impl._api_types.Error as exc:
            raise exc

    def __go_to_page(self, url):
        """Go to a page."""
        self.page.goto(url)
        time.sleep(2)
        context = self.__get_context()
        return {"context": context}

    def __preprocess_html_for_prompt(self) -> Dict:
        """Preprocess the HTML. Returns a a string representing a dict of the form:
        {
            "int": {
                "object": <element object>,
                "original": <original tag>,
                "transformed": <transformed tag>,
                "text": <text of the tag>
            }
        }
        """
        logger.info("Preprocessing HTML for AI to read...")

        # Get all of inputs, textareas, anchors, buttons, and imgs.
        inputs = self.page.locator("input").all()
        textareas = self.page.locator("textarea").all()
        anchors = self.page.locator("a").all()
        buttons = self.page.locator("button").all()
        imgs = self.page.locator("img").all()
        divs = self.page.locator("div").all()
        divs = [
            div for div in divs if div.get_attribute("role") in ["button", "textbox"]
        ]

        # Combine all of the elements.
        elements = inputs + textareas + anchors + buttons + imgs + divs

        mapping = {}
        curr_idx = 1
        for element in elements:
            tag_name = get_tag_name(element)

            # If the element is not visible, then don't include it.
            if not element.is_visible():
                continue
            old_element = get_outer_html(element)

            # Select the attributes to keep.
            attrs = {}
            attrs_to_keep = [
                "alt",
                "aria-label",
                "name",
                "title",
                "type",
                "role",
            ]
            for attr in attrs_to_keep:
                if element.get_attribute(attr):
                    attrs[attr] = str(element.get_attribute(attr))

            # If the element is an input, then add the value and the
            # placeholder.

            if tag_name == "input":
                input_value = str(element.get_attribute("value"))
                input_placeholder = str(element.get_attribute("placeholder"))
                if input_value:
                    attrs["value"] = input_value
                if input_placeholder:
                    attrs["placeholder"] = input_placeholder

            # Get the text from the element and strip whitespace.
            text = element.inner_text().replace("\n", " ")

            # Create the new element.
            bs_tag = Tag(name=tag_name, attrs=attrs)
            bs_tag["id"] = str(curr_idx)
            bs_tag.string = text
            new_element = str(bs_tag)

            # If the img has no alt text, then don't include it.
            # In the future, we could try to use computer vision to caption.
            if tag_name == "img" and not element.get_attribute("alt"):
                continue

            # If div, button, or anchor has no text, then don't include it.
            if tag_name in ["div", "a", "button"] and not text:
                continue

            mapping[curr_idx] = {
                "object": element,
                "original": old_element,
                "transformed": new_element,
                "text": text,
            }
            curr_idx += 1

        self._current_browser_mapping = mapping
        prompt_str = get_current_browser_view_from_mapping(mapping)
        return prompt_str
    
    def save_cookies(self, output_file):
        """Save cookies to a file."""
        cookies = self.browser_context.cookies()
        with open(output_file, "w") as f:
            f.write(json.dumps(cookies))


def main():
    """Test it out."""
    objective = "Go to https://google.com, search for 'cats', and click the first result. Wait 10 seconds. Then you're done."

    with sync_playwright() as playwright_obj:
        agent = PlaywrightAgent(playwright_obj, objective, verbose=True)
        agent.run()


if __name__ == "__main__":
    main()