import Link from "next/link";
import Image from "next/image";
import type { BlogPost } from "../../lib/blog";
import { formatDate } from "../../lib/blog";

interface BlogRelatedProps {
  posts: BlogPost[];
  /** If true, renders as a sidebar widget; otherwise renders as a full-width section */
  variant?: "sidebar" | "full";
}

export default function BlogRelated({
  posts,
  variant = "sidebar",
}: BlogRelatedProps) {
  if (posts.length === 0) return null;

  if (variant === "sidebar") {
    return (
      <aside
        className="rounded-xl p-5"
        style={{
          background: "var(--white)",
          border: "var(--divider-thin) solid var(--neutral-200)",
        }}
        aria-label="Related articles"
      >
        <p
          className="text-xs font-semibold uppercase tracking-wider mb-3"
          style={{ color: "var(--neutral-500)" }}
        >
          Related articles
        </p>
        <ul className="flex flex-col gap-0 list-none p-0 m-0">
          {posts.map((post, i) => (
            <li
              key={post.slug}
              style={{
                borderBottom:
                  i < posts.length - 1
                    ? "var(--divider-thin) solid var(--neutral-100)"
                    : "none",
              }}
            >
              <Link
                href={post.href}
                className="block py-3 no-underline"
                aria-label={`Read: ${post.title}`}
              >
                <p
                  className="text-sm font-medium line-clamp-2 mb-1"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {post.title}
                </p>
                <p className="text-xs" style={{ color: "var(--neutral-500)" }}>
                  <time dateTime={post.date}>{formatDate(post.date)}</time>
                  {" · "}
                  {post.readingTime} min read
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </aside>
    );
  }

  // Full-width section
  return (
    <section
      className="section-padding"
      style={{ background: "var(--surface-marketing)" }}
      aria-labelledby="related-posts-heading"
    >
      <div className="container-marketing">
        <h2
          id="related-posts-heading"
          className="text-section-title mb-12"
          style={{ color: "var(--neutral-900)" }}
        >
          Keep Reading
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {posts.map((post) => (
            <Link
              key={post.slug}
              href={post.href}
              className="card-marketing flex flex-col overflow-hidden no-underline"
              aria-label={`Read: ${post.title}`}
            >
              <div
                className="w-full overflow-hidden relative"
                style={{ aspectRatio: "16/9" }}
              >
                <Image
                  src={post.image}
                  alt={post.title}
                  fill
                  className="object-cover object-center"
                  sizes="(max-width: 48rem) 100vw, 33vw"
                />
              </div>
              <div className="p-5 flex flex-col flex-1">
                <h3
                  className="text-base font-semibold mb-2 line-clamp-2"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {post.title}
                </h3>
                <p
                  className="text-sm flex-1 line-clamp-2"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {post.description}
                </p>
                <p
                  className="text-xs mt-3"
                  style={{ color: "var(--neutral-500)" }}
                >
                  <time dateTime={post.date}>{formatDate(post.date)}</time>
                  {" · "}
                  {post.readingTime} min read
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
