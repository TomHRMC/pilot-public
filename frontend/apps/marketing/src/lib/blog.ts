import fs from "fs";
import path from "path";
import matter from "gray-matter";

/* ─── Types ──────────────────────────────────────────── */

export interface BlogPost {
  slug: string;
  title: string;
  description: string;
  author: string;
  date: string;
  category: string;
  tags: string[];
  trade: string;
  featured: boolean;
  image: string;
  readingTime: number;
  /** Relative URL path e.g. /blog/introducing-pilot-for-trades */
  href: string;
}

export type BlogCategory =
  | "electrical"
  | "plumbing"
  | "hvac"
  | "business"
  | "product"
  | "all";

/* ─── Constants ──────────────────────────────────────── */

export const BLOG_CATEGORIES: { slug: BlogCategory; label: string }[] = [
  { slug: "all", label: "All" },
  { slug: "electrical", label: "Electrical" },
  { slug: "plumbing", label: "Plumbing" },
  { slug: "hvac", label: "HVAC" },
  { slug: "business", label: "Business" },
  { slug: "product", label: "Product" },
];

const CONTENT_DIR = path.join(process.cwd(), "src", "content", "blog");

/* ─── Helpers ────────────────────────────────────────── */

function getCategoryDirs(): string[] {
  if (!fs.existsSync(CONTENT_DIR)) return [];
  return fs
    .readdirSync(CONTENT_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);
}

function parseFrontmatter(
  filePath: string,
  categoryDir: string,
): BlogPost | null {
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    const { data } = matter(raw);

    // Derive slug from filename if not in frontmatter
    const filename = path.basename(filePath, ".mdx");
    const slug = (data.slug as string) || filename;

    return {
      slug,
      title: (data.title as string) || "",
      description: (data.description as string) || "",
      author: (data.author as string) || "Tom Lang",
      date: (data.date as string) || "",
      category: (data.category as string) || categoryDir,
      tags: (data.tags as string[]) || [],
      trade: (data.trade as string) || categoryDir,
      featured: (data.featured as boolean) ?? false,
      image: (data.image as string) || "/blog/placeholder-hero.jpg",
      readingTime: (data.readingTime as number) || 5,
      href: `/blog/${slug}`,
    };
  } catch {
    return null;
  }
}

/* ─── Public API ─────────────────────────────────────── */

/**
 * Returns all blog posts sorted newest first.
 */
export function getAllPosts(): BlogPost[] {
  const dirs = getCategoryDirs();
  const posts: BlogPost[] = [];

  for (const dir of dirs) {
    const dirPath = path.join(CONTENT_DIR, dir);
    if (!fs.existsSync(dirPath)) continue;

    const files = fs
      .readdirSync(dirPath)
      .filter((f) => f.endsWith(".mdx") || f.endsWith(".md"));

    for (const file of files) {
      const post = parseFrontmatter(path.join(dirPath, file), dir);
      if (post) posts.push(post);
    }
  }

  // Sort newest first
  return posts.sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
  );
}

/**
 * Returns posts filtered by category (or all if category is "all").
 */
export function getPostsByCategory(category: BlogCategory): BlogPost[] {
  const all = getAllPosts();
  if (category === "all") return all;
  return all.filter((p) => p.category === category);
}

/**
 * Returns a single post's frontmatter + raw MDX content.
 */
export function getPostBySlug(
  slug: string,
): { post: BlogPost; content: string } | null {
  const dirs = getCategoryDirs();

  for (const dir of dirs) {
    const dirPath = path.join(CONTENT_DIR, dir);
    if (!fs.existsSync(dirPath)) continue;

    const files = fs
      .readdirSync(dirPath)
      .filter((f) => f.endsWith(".mdx") || f.endsWith(".md"));

    for (const file of files) {
      const filePath = path.join(dirPath, file);
      try {
        const raw = fs.readFileSync(filePath, "utf-8");
        const { data, content } = matter(raw);
        const fileSlug = (data.slug as string) || path.basename(file, ".mdx");

        if (fileSlug === slug) {
          const post = parseFrontmatter(filePath, dir);
          if (post) return { post, content };
        }
      } catch {
        continue;
      }
    }
  }

  return null;
}

/**
 * Returns all unique [slug, category] combinations for static generation.
 */
export function getAllPostSlugs(): { slug: string }[] {
  return getAllPosts().map((p) => ({ slug: p.slug }));
}

/**
 * Returns all unique category slugs that have at least one post.
 */
export function getAllCategorySlugs(): { category: string }[] {
  const all = getAllPosts();
  const cats = new Set(all.map((p) => p.category));
  return Array.from(cats).map((c) => ({ category: c }));
}

/**
 * Returns the featured post (featured:true + newest), falling back to most recent.
 */
export function getFeaturedPost(): BlogPost | null {
  const all = getAllPosts();
  if (all.length === 0) return null;
  return all.find((p) => p.featured) || all[0];
}

/**
 * Returns related posts: same category first, then tag overlap, then recency.
 * Excludes the current post. Returns up to `limit` items.
 */
export function getRelatedPosts(
  currentSlug: string,
  category: string,
  tags: string[],
  limit = 3,
): BlogPost[] {
  const all = getAllPosts().filter((p) => p.slug !== currentSlug);

  const scored = all.map((p) => {
    let score = 0;
    if (p.category === category) score += 10;
    const sharedTags = tags.filter((t) => p.tags.includes(t)).length;
    score += sharedTags * 2;
    return { post: p, score };
  });

  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((s) => s.post);
}

/**
 * Format date string to human-readable e.g. "Jun 15, 2026"
 */
export function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}
