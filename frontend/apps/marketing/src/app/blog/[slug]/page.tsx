// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MDXRemote } from "next-mdx-remote/rsc";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import rehypeSlug from "rehype-slug";
import rehypeAutolinkHeadings from "rehype-autolink-headings";
import {
  getAllPostSlugs,
  getPostBySlug,
  getRelatedPosts,
} from "../../../lib/blog";
import BlogPostLayout from "../../../components/blog/BlogPostLayout";
import BlogCta from "../../../components/blog/BlogCta";
import type { TocHeading } from "../../../components/blog/BlogToc";

/* ─── Static params for export ──────────────────────── */

export async function generateStaticParams() {
  return getAllPostSlugs();
}

/* ─── Metadata ──────────────────────────────────────── */

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const result = getPostBySlug(slug);
  if (!result) return {};

  const { post } = result;
  return {
    title: post.title,
    description: post.description,
    openGraph: {
      title: `${post.title} | Pilot for Trades`,
      description: post.description,
      url: `https://pilotfortrades.com/blog/${post.slug}`,
      type: "article",
      publishedTime: post.date,
      authors: [post.author],
      images: [
        {
          url: post.image.startsWith("/")
            ? `https://pilotfortrades.com${post.image}`
            : post.image,
          width: 1200,
          height: 630,
          alt: post.title,
        },
      ],
    },
  };
}

/* ─── Extract headings from MDX content ─────────────── */

function extractHeadings(content: string): TocHeading[] {
  const headingRegex = /^(#{2,3})\s+(.+)$/gm;
  const headings: TocHeading[] = [];
  let match;

  while ((match = headingRegex.exec(content)) !== null) {
    const level = match[1].length as 2 | 3;
    const text = match[2].trim();
    // Replicate rehype-slug's id generation: lowercase, replace spaces with hyphens
    const id = text
      .toLowerCase()
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .trim();
    headings.push({ id, text, level });
  }

  return headings;
}

/* ─── MDX components ─────────────────────────────────── */

const mdxComponents = {
  BlogCta: (props: Parameters<typeof BlogCta>[0]) => <BlogCta {...props} />,
};

/* ─── Page ───────────────────────────────────────────── */

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = getPostBySlug(slug);
  if (!result) notFound();

  const { post, content } = result;
  const relatedPosts = getRelatedPosts(post.slug, post.category, post.tags);
  const headings = extractHeadings(content);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.description,
    author: {
      "@type": "Person",
      name: post.author,
    },
    datePublished: post.date,
    image: post.image.startsWith("/")
      ? `https://pilotfortrades.com${post.image}`
      : post.image,
    url: `https://pilotfortrades.com/blog/${post.slug}`,
    publisher: {
      "@type": "Organization",
      name: "Pilot for Trades",
      url: "https://pilotfortrades.com",
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <BlogPostLayout
        post={post}
        relatedPosts={relatedPosts}
        headings={headings}
      >
        <MDXRemote
          source={content}
          components={mdxComponents}
          options={{
            mdxOptions: {
              remarkPlugins: [remarkGfm],
              rehypePlugins: [
                rehypeHighlight,
                rehypeSlug,
                [
                  rehypeAutolinkHeadings,
                  {
                    behavior: "append",
                    properties: {
                      className: ["anchor-link"],
                      ariaLabel: "Link to section",
                    },
                  },
                ],
              ],
            },
          }}
        />
      </BlogPostLayout>
    </>
  );
}
