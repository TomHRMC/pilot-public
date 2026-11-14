import Link from "next/link";
import type { BlogPost } from "../../lib/blog";
import { formatDate } from "../../lib/blog";

const CATEGORY_COLORS: Record<
  string,
  { bg: string; text: string; dot: string }
> = {
  electrical: {
    bg: "var(--trade-electrical-10)",
    text: "var(--trade-electrical-text)",
    dot: "var(--trade-electrical)",
  },
  plumbing: {
    bg: "var(--trade-plumbing-10)",
    text: "var(--trade-plumbing-text)",
    dot: "var(--trade-plumbing)",
  },
  hvac: {
    bg: "var(--trade-hvac-10)",
    text: "var(--trade-hvac-text)",
    dot: "var(--trade-hvac)",
  },
  business: {
    bg: "var(--brand-50)",
    text: "var(--brand-800)",
    dot: "var(--brand-600)",
  },
  product: {
    bg: "var(--brand-50)",
    text: "var(--brand-800)",
    dot: "var(--brand-600)",
  },
};

function CategoryBadge({ category }: { category: string }) {
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.product;
  const label = category.charAt(0).toUpperCase() + category.slice(1);
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider rounded-full px-3 py-1"
      style={{ background: colors.bg, color: colors.text }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ background: colors.dot }}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}

interface BlogCardProps {
  post: BlogPost;
  className?: string;
}

export default function BlogCard({ post, className = "" }: BlogCardProps) {
  return (
    <Link
      href={post.href}
      className={`card-marketing flex flex-col overflow-hidden no-underline ${className}`}
      aria-label={`Read: ${post.title}`}
    >
      {/* Thumbnail */}
      <div
        className="w-full overflow-hidden"
        style={{
          aspectRatio: "16/9",
          background: "var(--surface-marketing-alt)",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={post.image}
          alt={post.title}
          width={600}
          height={338}
          className="w-full h-full object-cover"
          loading="lazy"
          decoding="async"
        />
      </div>

      {/* Content */}
      <div className="flex flex-col flex-1 p-5">
        <div className="mb-3">
          <CategoryBadge category={post.category} />
        </div>

        <h3
          className="text-lg font-semibold mb-2 line-clamp-2"
          style={{ color: "var(--neutral-900)" }}
        >
          {post.title}
        </h3>

        <p
          className="text-sm mb-4 flex-1 line-clamp-3"
          style={{ color: "var(--neutral-600)" }}
        >
          {post.description}
        </p>

        {/* Meta */}
        <div
          className="flex items-center gap-2 text-xs"
          style={{ color: "var(--neutral-500)" }}
        >
          <span>{post.author}</span>
          <span aria-hidden="true">·</span>
          <time dateTime={post.date}>{formatDate(post.date)}</time>
          <span aria-hidden="true">·</span>
          <span>{post.readingTime} min read</span>
        </div>
      </div>
    </Link>
  );
}

export { CategoryBadge };
