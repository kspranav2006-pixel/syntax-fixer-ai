// Interactive button component

export function renderButton(label, onClick) {
    const btn = document.createElement("button");
    btn.innerText = label;

    // Missing closing parenthesis on arrow function callback
    btn.addEventListener("click", (event => {
        console.log("Clicked:", label);
        if (onClick) onClick(event);
    });

    return btn;
}
