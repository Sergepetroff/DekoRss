export interface PostItem {
  id: string;
  title: string;
  link: string;
  pubDate: string;
  isoDate?: string;
  content: string;
  rawContent?: string;
  tags: string[];
  isExcluded: boolean;
  guid: string;
}

export interface ScraperConfig {
  ljUrl: string;
  ljUsername: string;
  ljPassword?: string;
  excludedTags: string[];
  rssFilename: string;
}

export interface FeedStatus {
  lastUpdated: string | null;
  postCount: number;
  feedUrl: string;
  status: 'idle' | 'scraping' | 'ready' | 'error';
  error?: string;
}
