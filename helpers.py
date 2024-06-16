"""
Helper functions 
"""
import json


def get_filtered_elements(page):
    with open("js/mark_page.js") as f:
        js = f.read()

    page.evaluate(js)
    elements = page.evaluate("markPage()")
    page.evaluate("unmarkPage()")

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

    return clean_elements


def parse_json_garbage(s):
    s = s[next(idx for idx, c in enumerate(s) if c in "{["):]
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        return json.loads(s[:e.pos])
    

def get_actions_taken(actions: list):
    filtered_actions = []
    for action in actions:
        action_bullet_str = "- " + action["command"]["action"]
        if "args" in action["command"]:
            action_bullet_str += " with args " + str(action["command"]["args"])

    cleaned_actions = str("\n".join(filtered_actions))

    if cleaned_actions.strip():
        return actions
    else:
        return "None."
    
def get_actions_taken_with_thoughts(actions: list):
    print(actions)
    filtered_actions = []
    for action in actions:
        action_bullet_str = "- " + action["command"]["action"]
        # if "args" in action["command"]:
        #     action_bullet_str += " with args " + str(action["command"]["args"])
        if "thoughts" in action:
            action_bullet_str += " with thoughts " + action["thoughts"]["text"]

    cleaned_actions = str("\n".join(filtered_actions))
    print("Cleaned actions: ", cleaned_actions)

    if cleaned_actions.strip():
        return actions
    else:
        exit()
        return "None."
    
