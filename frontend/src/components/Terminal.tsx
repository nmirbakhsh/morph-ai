import { useEffect, useRef } from "react";

interface Props {
  logs: string[];
}

export function Terminal({ logs }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [logs.length]);

  return (
    <div className="terminal-overlay">
      <div className="terminal-box" ref={ref}>
        {logs.map((line, i) => {
          const cls =
            line.startsWith("$") ? "cmd" :
            line.startsWith("✗") ? "err" :
            line.startsWith("✓") ? "ok" : "";
          return <div className={`terminal-line ${cls}`} key={i}>{line}</div>;
        })}
        <div>
          <span className="terminal-cursor" />
        </div>
      </div>
    </div>
  );
}
