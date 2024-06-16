import asyncio
import time
import json
from helpers import get_filtered_elements
# from playwright.async_api import async_playwright, Playwright
from playwright.sync_api import sync_playwright, Playwright
from agent import ActionAgent, PragyaGPT


done = False

def mark_page(page):
    with open("js/mark_page.js") as f:
        js = f.read()

    page.evaluate(js)
    elements = page.evaluate("markPage()")
    # print(elements)
    # try:
    #     page.screenshot(path="screenshot.png")
    # except Exception as e:
    #     print("Error (line 28): "+str(e))
    page.evaluate("unmarkPage()")
    
    with open("elements.json", "w") as f:
        json.dump(elements, f, indent=4)

    clean_elements = []
    for element in elements:
        if element["text"] or element["ariaLabel"] or element["placeholder"] or element["label"]:
            clean_element = {}
            clean_element["text"] = element["text"]
            clean_element["ariaLabel"] = element["ariaLabel"]
            clean_element["path"] = element["path"]
            clean_element["placeholder"] = element["placeholder"]
            clean_element["label"] = element["label"]
            clean_elements.append(clean_element)

    with open("clean_elements.json", "w") as f:
        json.dump(clean_elements, f, indent=4)
    return clean_elements

def clean_elements_id_based(current_page_elements, current_url):
    clean_elements = []
    i = 0
    for element in current_page_elements:
        if "https://www.google.com/search" in current_url and str(element["ariaLabel"]) == "Search":
            continue
        if "https://www.google.com/search" in current_url and str(element["text"]) == "Tools":
            continue
        clean_element = {}
        clean_element["id"] = i
        if element["text"]:
            clean_element["text"] = element["text"]
        if element["ariaLabel"]:
            clean_element["ariaLabel"] = element["ariaLabel"]
        if element["placeholder"]:
            clean_element["placeholder"] = element["placeholder"]
        if element["label"]:
            clean_element["label"] = element["label"]
        clean_elements.append(clean_element)
        i += 1

    return clean_elements


def run(playwright: Playwright):
    user_objective = str(input("> Enter your objective: "))
    chromium = playwright.chromium # or "firefox" or "webkit".
    options = {
        'args': [
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-setuid-sandbox',
            '--no-first-run',
            '--no-sandbox',
            '--no-zygote',
            '--ignore-certificate-errors',
            '--disable-extensions',
            '--disable-infobars',
            '--disable-notifications',
            '--disable-popup-blocking',
            '--remote-debugging-port=9222',
            '--start-maximized',
            '--disable-blink-features=AutomationControlled'
        ],
        'headless': False  # Set headless option here
    }

    # Launch Chrome browser with options
    # browser = chromium.launch(**options)
    browser = chromium.launch(headless=True, args=['--start-maximized'])
    page = browser.new_page(no_viewport=True)

    agent = ActionAgent(page)
    pragya = PragyaGPT()

    final_goal = pragya.get_final_goal(user_objective)
    print("\n\nFINAL GOAL:\n")
    print(final_goal)
    print("\n")

    #  F I R S T   S T E P

    trail_left = 5
    error=None
    while trail_left > 0:
        try:
            first_step = pragya.get_first_step(user_objective, error)
            if "args" in first_step["command"]:
                action_args = first_step["command"]["args"]

            agent.execute(first_step["command"]["action"], *action_args)
            agent.wait_till_idle()

            trail_left = 5
            error = None

            break
        except Exception as e:
            print("Error (line 115): "+str(e))
            error = str(e)
            trail_left -= 1
            print(f"\nTRIAL LEFT: {trail_left} times\n")

    #  O B S E R V A T I O N  O F  F I R S T  S T E P

    current_url = page.url
    current_page_elements = mark_page(page)
    clean_elements = clean_elements_id_based(current_page_elements, current_url)
    observation = pragya._observation(current_url, clean_elements)
    print("\n\nOBSERVATION (line 83):\n")
    print(observation)
    print("\n")

    #  N E X T  S T E P  L O O P

    _ = 0

    while not agent.get_goal_achieved() and trail_left > 0:
        try:
            # NEXT STEP
            current_url = page.url
            current_page_elements = mark_page(page)
            clean_elements = clean_elements_id_based(current_page_elements, current_url)
            with open("clean_elements_id_based.json", "w") as f:
                json.dump(clean_elements, f, indent=4)
            _ += 1
            print(f"Entering next step x{_}!!")
            next_step = pragya._next_action(objective=user_objective, current_page_elements=clean_elements, current_url=current_url, error=error)
            print("Next step done!!")

            if next_step["command"]["action"] == "_click" or next_step["command"]["action"] == "_type":
                if "id" in str(next_step["command"]["args"][0]):
                    # just take out whatever number is present in the string
                    next_step["command"]["args"][0] = int(''.join(filter(str.isdigit, next_step["command"]["args"][0])))
                next_step["command"]["args"][0] = current_page_elements[int(next_step["command"]["args"][0])]["path"]
                print(f"Next step args: {next_step['command']['args']}.")

            if "args" in next_step["command"]:
                action_args = next_step["command"]["args"]

            # EXECUTE NEXT STEP

            agent.execute(next_step["command"]["action"], *action_args)
            agent.wait_till_idle()

            # OBSERVATION OF NEXT STEP

            current_url = page.url
            current_page_elements = mark_page(page)
            clean_elements = clean_elements_id_based(current_page_elements, current_url)
            observation = pragya._observation(current_url, clean_elements)
            print("\n\nOBSERVATION:\n")
            print(observation)
            print("\n")

            trail_left = 5
            error = None
            
        except Exception as e:
            print("Error (line 175): "+str(e))
            error = str(e)
            trail_left -= 1
            print(f"\nTRIAL LEFT: {trail_left} times\n")

    agent._wait(5)
    print("\n\nFINALLY GOAL ACHIEVED!! 🥳\n\n") if not error else print(f"\n\nERROR OCCURED!! 😢\n{error}\n\n")
    browser.close()



# async def start():
#     async with async_playwright() as playwright:
#         await run(playwright)
# asyncio.run(start())

with sync_playwright() as playwright:
    run(playwright)
