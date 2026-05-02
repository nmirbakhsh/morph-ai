import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function TextBlockView({ block }) {
    return (_jsxs("div", { className: "text-block", children: [block.title && _jsx("div", { className: "text-block-title", children: block.title }), _jsx("div", { className: "text-block-body", children: block.body })] }));
}
