const customCSS = `
    ::-webkit-scrollbar {
        width: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #27272a;
    }
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 0.375rem;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
`;

const styleTag = document.createElement("style");
styleTag.textContent = customCSS;
document.head.append(styleTag);

let labels = [];

function unmarkPage() {
  // Unmark page logic
  for (const label of labels) {
    document.body.removeChild(label);
  }
  labels = [];
}

function getPathTo(element) {
  if (element.id !== '')
    return 'id("' + element.id + '")';
  if (element === document.body)
    return element.tagName;

  var ix = 0;
  var siblings = element.parentNode.childNodes;
  for (var i = 0; i < siblings.length; i++) {
    var sibling = siblings[i];
    if (sibling === element)
      return getPathTo(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
    if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
      ix++;
  }
}

function markPage() {
  unmarkPage();

  let bodyRect = document.body.getBoundingClientRect();

  // Get all elements on the page and filter out the ones that are not clickable
  let items = Array.prototype.slice
    .call(document.querySelectorAll("*"))
    .map(function (element, index) {
      let vw = Math.max(
        document.documentElement.clientWidth || 0,
        window.innerWidth || 0
      );
      let vh = Math.max(
        document.documentElement.clientHeight || 0,
        window.innerHeight || 0
      );
      let textualContent = element.textContent.trim().replace(/\s{2,}/g, " ");
      let elementType = element.tagName.toLowerCase();
      let ariaLabel = element.getAttribute("aria-label") || "";
      let placeholder = element.getAttribute("placeholder") || "";
      let label = ""; // Initialize label variable

      // Check if the element has a label associated with it
      const labelElement = element.closest("label");
      if (labelElement) {
        label = labelElement.textContent.trim();
      }

      // save xpath of the element
      path = getPathTo(element);

      let rects = [...element.getClientRects()]
        .filter((bb) => {
          let center_x = bb.left + bb.width / 2;
          let center_y = bb.top + bb.height / 2;
          let elAtCenter = document.elementFromPoint(center_x, center_y);

          return elAtCenter === element || element.contains(elAtCenter);
        })
        .map((bb) => {
          const rect = {
            left: Math.max(0, bb.left),
            top: Math.max(0, bb.top),
            right: Math.min(vw, bb.right),
            bottom: Math.min(vh, bb.bottom),
          };
          return {
            ...rect,
            width: rect.right - rect.left,
            height: rect.bottom - rect.top,
          };
        });

      let area = rects.reduce((acc, rect) => acc + rect.width * rect.height, 0);

      return {
        element: element,
        path: path,
        include:
          element.tagName === "INPUT" ||
          element.tagName === "TEXTAREA" ||
          element.tagName === "SELECT" ||
          element.tagName === "BUTTON" ||
          element.tagName === "A" ||
          element.onclick != null ||
          window.getComputedStyle(element).cursor == "pointer" ||
          element.tagName === "IFRAME" ||
          element.tagName === "VIDEO",
        area,
        rects,
        text: textualContent,
        type: elementType,
        ariaLabel: ariaLabel,
        placeholder: placeholder,
        label: label, // Assign label to the item
      };
    })
    .filter((item) => item.include && item.area >= 20);

  // Only keep inner clickable items 
  items = items.filter(
    (x) => !items.some((y) => x.element.contains(y.element) && !(x == y))
  );

  const clickableItems =
    items.map((item) => ({
      text: item.text,
      type: item.type,
      ariaLabel: item.ariaLabel,
      path: item.path,
      placeholder: item.placeholder,
      label: item.label,
      type: item.type,
    }));

  // Lets create a floating border on top of these elements that will always be visible
  items.forEach(function (item, index) {
    item.rects.forEach((bbox) => {
      newElement = document.createElement("div");
      const borderColor = "#00FF00";
      newElement.style.outline = `2px solid ${borderColor}`;
      newElement.style.position = "fixed";
      newElement.style.left = bbox.left + "px";
      newElement.style.top = bbox.top + "px";
      newElement.style.width = bbox.width + "px";
      newElement.style.height = bbox.height + "px";
      newElement.style.pointerEvents = "none";
      newElement.style.boxSizing = "border-box";
      newElement.style.zIndex = 2147483647;
      // newElement.style.background = `${borderColor}80`;

      // // Add floating label at the corner
      // let label = document.createElement("span");
      // label.textContent = index;
      // label.style.position = "absolute";
      // // These we can tweak if we want
      // label.style.top = "-19px";
      // label.style.left = "0px";
      // label.style.background = borderColor;
      // // label.style.background = "black";
      // label.style.color = "white";
      // label.style.padding = "2px 4px";
      // label.style.fontSize = "12px";
      // label.style.borderRadius = "2px";
      // newElement.appendChild(label);

      document.body.appendChild(newElement);
      labels.push(newElement);
      // item.element.setAttribute("-ai-label", label.textContent);
    });
  });
  // const coordinates = items.flatMap((item) =>
  //   item.rects.map(({ left, top, width, height }) => ({
  //     x: (left + left + width) / 2,
  //     y: (top + top + height) / 2,
  //     type: item.type,
  //     text: item.text,
  //     ariaLabel: item.ariaLabel,
  //   }))
  // );
  // return coordinates;
  return clickableItems;
}