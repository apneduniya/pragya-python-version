FIRST_STEP_ACTION_DESCRIPTION_PROMPT = """You are given the following objective: "{objective}" and the following final goal needs to be achieved: "{final_goal}".

You can use the following actions which will help you to control the browser:
1. _google_search(text)
2. _go_to_url(url)
3. _click(id)
4. _type(id, text)
5. _scroll_up()
6. _scroll_down()
7. _wait()
8. _go_back()
9. _set_goal_achieved()

ERROR:
{error}
"""
# You have taken the following actions so far. Try not to repeat yourself unless necessary.
# {actions_taken}

FIRST_STEP_ACTION_GOAL_PROMPT = """What will be your next action ensuring the a solid start? Please choose only ONE action at a time. Answer with a JSON with the below form which can be loaded with Python `json.loads`. Example:
{
    "thoughts": {
        "text": "<your thought>",
        "reasoning": "<your reasoning>"
    },
    "command": {
        "action": "_selected_action_name",
        "args": ["arg1", "arg2"],
    }
}

REMEMBER:
- You should provide thoughts and reasoning for your action.
- Your response should be in JSON format with the above structure.
- Use the action `_set_goal_achieved()` only when the final goal is achieved, not before that.
- Don't give more arguments than the action can take.
- Don't choose any other actions other than the ones mentioned above.
- Read the error and try to avoid it in the next action.
"""


NEXT_STEP_ACTION_DESCRIPTION_PROMPT = """You are given the following objective: "{objective}" and the following final goal needs to be achieved: "{final_goal}".

You have taken the following actions so far. Try not to repeat yourself unless necessary.
{actions_taken}

You can use the following actions which will help you to control the browser:
1. _click(id)
2. _type(id, text)
3. _scroll_up()
4. _scroll_down() # To see more content
5. _wait()
6. _go_back()
7. _set_goal_achieved() # ONLY USE THIS ACTION WHEN THE FINAL GOAL IS ACHIEVED
8. _google_search(text) # ONLY USE IF ALL THE ABOVE ACTIONS ARE NOT APPLICABLE
9. _go_to_url(url)

Observation of the current page:
{observation}

Current URL: {current_url}

Current Page Elements(every element is clickable): 
{current_page_elements}
The format of the browser content is highly simplified; all formatting elements are stripped.
When choosing elements, please use the `id` number.

ERROR (try to give response avoiding this error):
{error}
"""

NEXT_STEP_ACTION_GOAL_PROMPT = """What will be your next action ensuring the final goal is achieved? Please choose only ONE action at a time. Answer with a JSON with the below form which can be loaded with Python `json.loads`. Example:
{
    "thoughts": {
        "text": "<your thought>",
        "reasoning": "<your reasoning>"
    },
    "command": {
        "action": "_selected_action_name",
        "args": ["arg1", "arg2"],
    }
}

Your response must obey the following constraints:
- You should provide thoughts and reasoning for your action.
- Your response should be in JSON format with the above structure.
- Try not to repeat yourself unless necessary.
- Use the action `_set_goal_achieved()` only when the final goal is achieved, not before that.
- Don't give more arguments than the action can take.
- Don't choose any other actions other than the ones mentioned above.
- Only select that element which will help you to achieve the final goal most possibly in whole list.

TIPS:
- When you are clicking on an element, make sure that element text or label or ariaLabel or placeholder contains any words of the final goal or objective the most!
"""

