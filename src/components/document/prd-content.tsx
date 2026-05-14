"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeSanitize from "rehype-sanitize"

interface PrdContentProps {
  content: string
}

export function PrdContent({ content }: PrdContentProps) {
  return (
    <div className="rounded-xl bg-card shadow-[var(--shadow-card)]" style={{ padding: "clamp(1.25rem, 3vw, 2.5rem)" }}>
      <div className="prose prose-sm sm:prose-base dark:prose-invert mx-auto max-w-[72ch]">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeSanitize]}
          components={{
            a: ({ children, href, ...props }) => (
              <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  )
}
