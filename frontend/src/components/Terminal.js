import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef } from "react";
export function Terminal({ logs }) {
    const ref = useRef(null);
    useEffect(() => {
        if (ref.current)
            ref.current.scrollTop = ref.current.scrollHeight;
    }, [logs.length]);
    return (_jsx("div", { className: "terminal-overlay", children: _jsxs("div", { className: "terminal-box", ref: ref, children: [logs.map((line, i) => {
                    const cls = line.startsWith("$") ? "cmd" :
                        line.startsWith("✗") ? "err" :
                            line.startsWith("✓") ? "ok" : "";
                    return _jsx("div", { className: `terminal-line ${cls}`, children: line }, i);
                }), _jsx("div", { children: _jsx("span", { className: "terminal-cursor" }) })] }) }));
}
