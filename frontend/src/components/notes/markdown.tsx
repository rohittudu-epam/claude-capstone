import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders note Markdown. react-markdown does not render raw HTML (no rehype-raw here) and strips unsafe
 * URL schemes such as javascript:, so note content cannot inject script. External links open safely.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer nofollow" />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
