from agent import ActionAgent



agent = ActionAgent()
agent._open("https://www.google.com")
agent._type("input[name='q']", "SeleniumBase\n")
agent._assert_text("h3", "SeleniumBase")
agent._assert_element("h3")
agent._assert_url("https://www.google.com")
agent._highlight("h3")
agent._wait_for_element_visible("h3")
