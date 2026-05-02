import { jsx as _jsx } from "react/jsx-runtime";
export function TagRowView({ block }) {
    return (_jsx("div", { className: "tag-row", children: block.tags.map((t, i) => (_jsx("span", { className: "tag", children: t }, i))) }));
}
