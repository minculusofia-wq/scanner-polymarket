"""
News Aggregation Service.

Aggregates news from multiple sources:
- Google News RSS (free)
- NewsAPI (with API key)
- SerpAPI (with API key)
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
import asyncio
import httpx
import os


class Sentiment(Enum):
    """Sentiment classification."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class NewsItem:
    """A news item from any source."""
    id: str
    source: str           # google, newsapi, serpapi
    title: str
    content: str
    url: str
    sentiment: Sentiment
    sentiment_score: float  # -1 to 1
    keywords: List[str]
    published_at: datetime
    fetched_at: datetime


class NewsAggregator:
    """
    Service for aggregating news from multiple sources.
    
    Sources:
    - Google News RSS (free)
    - NewsAPI (requires API key)
    - SerpAPI (requires API key)
    """
    
    def __init__(self):
        self._news_cache: Dict[str, List[NewsItem]] = {}
        self._client: Optional[httpx.AsyncClient] = None
        
        # API Keys from environment
        self.newsapi_key = os.getenv("NEWSAPI_KEY", "")
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")
        
        # Keywords to track
        self._keywords = [
            "polymarket", "prediction market",
            "bitcoin", "ethereum", "crypto",
            "election", "trump", "biden",
            "fed", "interest rate", "inflation"
        ]
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def fetch_all(self) -> List[NewsItem]:
        """
        Fetch news from all sources.
        
        Returns:
            List of news items
        """
        tasks = [
            self._fetch_google_news(),
        ]
        
        # Add NewsAPI if key is configured
        if self.newsapi_key:
            tasks.append(self._fetch_newsapi())
        
        # Add SerpAPI if key is configured
        if self.serpapi_key:
            tasks.append(self._fetch_serpapi())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                print(f"Error fetching news: {result}")
        
        # Update cache
        for item in all_news:
            if item.source not in self._news_cache:
                self._news_cache[item.source] = []
            self._news_cache[item.source].append(item)
            
            # Keep only last 100 per source
            if len(self._news_cache[item.source]) > 100:
                self._news_cache[item.source] = self._news_cache[item.source][-100:]
        
        # Sort by publish date
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        
        return all_news
    
    async def _fetch_google_news(self) -> List[NewsItem]:
        """Fetch news from Google News RSS."""
        client = await self._get_client()
        news_items = []
        
        for keyword in ["polymarket", "prediction market crypto", "bitcoin price"]:
            try:
                url = f"https://news.google.com/rss/search?q={keyword}&hl=en-US&gl=US&ceid=US:en"
                response = await client.get(url)
                
                if response.status_code == 200:
                    items = self._parse_rss(response.text, keyword)
                    news_items.extend(items)
                    
            except Exception as e:
                print(f"Error fetching Google News for {keyword}: {e}")
        
        return news_items[:20]
    
    async def _fetch_newsapi(self) -> List[NewsItem]:
        """
        Fetch news from NewsAPI.
        
        Docs: https://newsapi.org/docs
        """
        if not self.newsapi_key:
            return []
        
        client = await self._get_client()
        news_items = []
        
        try:
            # Search for crypto/prediction market news
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": "polymarket OR prediction market OR bitcoin OR ethereum",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": self.newsapi_key
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                
                for article in articles:
                    try:
                        title = article.get("title", "")
                        description = article.get("description", "") or ""
                        
                        # Analyze sentiment
                        sentiment, score = self._analyze_sentiment(f"{title} {description}")
                        
                        # Parse date
                        pub_date = datetime.utcnow()
                        if article.get("publishedAt"):
                            try:
                                dt = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                                # Convert to naive UTC
                                pub_date = dt.replace(tzinfo=None)
                            except:
                                pass
                        
                        news_items.append(NewsItem(
                            id=f"newsapi_{hash(article.get('url', '')) % 10**8}",
                            source="newsapi",
                            title=title,
                            content=description,
                            url=article.get("url", ""),
                            sentiment=sentiment,
                            sentiment_score=score,
                            keywords=["newsapi"],
                            published_at=pub_date,
                            fetched_at=datetime.utcnow()
                        ))
                    except Exception as e:
                        continue
                
                print(f"📰 NewsAPI: Fetched {len(news_items)} articles")
            else:
                print(f"NewsAPI error: {response.status_code} - {response.text[:200]}")
                
        except Exception as e:
            print(f"Error fetching from NewsAPI: {e}")
        
        return news_items
    
    async def _fetch_serpapi(self) -> List[NewsItem]:
        """
        Fetch news from SerpAPI (Google News).
        
        Docs: https://serpapi.com/google-news-api
        """
        if not self.serpapi_key:
            return []
        
        client = await self._get_client()
        news_items = []
        
        try:
            url = "https://serpapi.com/search.json"
            params = {
                "engine": "google_news",
                "q": "polymarket OR crypto prediction market",
                "gl": "us",
                "hl": "en",
                "api_key": self.serpapi_key
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                news_results = data.get("news_results", [])
                
                for article in news_results:
                    try:
                        title = article.get("title", "")
                        snippet = article.get("snippet", "") or ""
                        
                        # Analyze sentiment
                        sentiment, score = self._analyze_sentiment(f"{title} {snippet}")
                        
                        # Parse date
                        pub_date = datetime.utcnow()
                        if article.get("date"):
                            # SerpAPI returns relative dates like "2 hours ago"
                            date_str = article["date"]
                            pub_date = self._parse_relative_date(date_str)
                        
                        news_items.append(NewsItem(
                            id=f"serpapi_{hash(article.get('link', '')) % 10**8}",
                            source="serpapi",
                            title=title,
                            content=snippet,
                            url=article.get("link", ""),
                            sentiment=sentiment,
                            sentiment_score=score,
                            keywords=["serpapi"],
                            published_at=pub_date,
                            fetched_at=datetime.utcnow()
                        ))
                    except Exception as e:
                        continue
                
                print(f"🔍 SerpAPI: Fetched {len(news_items)} articles")
            else:
                print(f"SerpAPI error: {response.status_code}")
                
        except Exception as e:
            print(f"Error fetching from SerpAPI: {e}")
        
        return news_items
    
    def _parse_relative_date(self, date_str: str) -> datetime:
        """Parse relative date strings like '2 hours ago'."""
        now = datetime.utcnow()
        date_str = date_str.lower()
        
        try:
            if "minute" in date_str:
                minutes = int(''.join(filter(str.isdigit, date_str)) or '1')
                return now - timedelta(minutes=minutes)
            elif "hour" in date_str:
                hours = int(''.join(filter(str.isdigit, date_str)) or '1')
                return now - timedelta(hours=hours)
            elif "day" in date_str:
                days = int(''.join(filter(str.isdigit, date_str)) or '1')
                return now - timedelta(days=days)
            elif "week" in date_str:
                weeks = int(''.join(filter(str.isdigit, date_str)) or '1')
                return now - timedelta(weeks=weeks)
        except:
            pass
        
        return now
    
    def _parse_rss(self, content: str, source_keyword: str) -> List[NewsItem]:
        """Parse RSS feed content."""
        import re
        from html import unescape
        
        items = []
        
        item_pattern = r"<item>(.*?)</item>"
        title_pattern = r"<title>(.*?)</title>"
        link_pattern = r"<link>(.*?)</link>"
        pubdate_pattern = r"<pubDate>(.*?)</pubDate>"
        
        for match in re.finditer(item_pattern, content, re.DOTALL):
            try:
                item_content = match.group(1)
                
                title_match = re.search(title_pattern, item_content)
                link_match = re.search(link_pattern, item_content)
                pubdate_match = re.search(pubdate_pattern, item_content)
                
                if title_match and link_match:
                    title = unescape(title_match.group(1))
                    url = link_match.group(1)
                    
                    pub_date = datetime.utcnow()
                    if pubdate_match:
                        try:
                            from email.utils import parsedate_to_datetime
                            dt = parsedate_to_datetime(pubdate_match.group(1))
                            # Convert to naive UTC
                            if dt.tzinfo:
                                dt = dt.astimezone(timezone.utc)
                            pub_date = dt.replace(tzinfo=None)
                        except:
                            pass
                    
                    sentiment, score = self._analyze_sentiment(title)
                    
                    items.append(NewsItem(
                        id=f"google_{hash(url) % 10**8}",
                        source="google_news",
                        title=title,
                        content=title,
                        url=url,
                        sentiment=sentiment,
                        sentiment_score=score,
                        keywords=[source_keyword],
                        published_at=pub_date,
                        fetched_at=datetime.utcnow()
                    ))
            except Exception as e:
                continue
        
        return items
    
    def _analyze_sentiment(self, text: str) -> tuple[Sentiment, float]:
        """Analyze sentiment of text using keyword matching."""
        text_lower = text.lower()
        
        positive_words = [
            "surge", "gain", "win", "success", "bullish", "up", "rise", 
            "growth", "positive", "rally", "soar", "jump", "record",
            "approval", "accept", "pass", "victory", "boom", "profit"
        ]
        negative_words = [
            "fall", "drop", "crash", "fail", "bearish", "down", "decline",
            "loss", "negative", "plunge", "sink", "tumble", "reject",
            "denial", "lawsuit", "fraud", "scam", "collapse", "crisis"
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return Sentiment.NEUTRAL, 0.0
        
        score = (positive_count - negative_count) / total
        
        if score > 0.2:
            return Sentiment.POSITIVE, score
        elif score < -0.2:
            return Sentiment.NEGATIVE, score
        else:
            return Sentiment.NEUTRAL, score
    
    def get_news_for_market(self, market_question: str, hours: int = 24) -> List[NewsItem]:
        """Get news relevant to a specific market."""
        keywords = market_question.lower().split()[:5]
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        relevant = []
        
        for source, items in self._news_cache.items():
            for item in items:
                if item.published_at < cutoff:
                    continue
                if any(kw in item.title.lower() for kw in keywords):
                    relevant.append(item)
        
        return sorted(relevant, key=lambda x: x.published_at, reverse=True)
    
    def get_news_score(self, market_question: str) -> int:
        """Calculate a news score (0-100) for a market."""
        news = self.get_news_for_market(market_question, hours=24)
        
        if not news:
            return 50
        
        total_score = sum(item.sentiment_score for item in news)
        avg_score = total_score / len(news)
        normalized = int((avg_score + 1) * 50)
        volume_boost = min(len(news) * 5, 20)
        
        return min(normalized + volume_boost, 100)
    
    def get_all_cached_news(self, limit: int = 50) -> List[NewsItem]:
        """Get all cached news from all sources."""
        all_news = []
        for items in self._news_cache.values():
            all_news.extend(items)
        
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        return all_news[:limit]
    
    def get_sources_status(self) -> Dict[str, bool]:
        """Get status of each news source."""
        return {
            "google_news": True,  # Always available
            "newsapi": bool(self.newsapi_key),
            "serpapi": bool(self.serpapi_key),
        }


# Singleton instance
news_aggregator = NewsAggregator()
