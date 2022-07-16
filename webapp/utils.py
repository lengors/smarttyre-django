import cutils
import importlib.util

from typing import List, Type


def load_crawler(script: str) -> List[Type[cutils.TyreCrawler]]:
    # Create a temporary module to import the crawler
    crawler_spec = importlib.util.spec_from_loader('crawler', None)
    crawler_module = importlib.util.module_from_spec(crawler_spec)

    # Try to load the crawler
    exec(script, crawler_module.__dict__)

    # Find the crawler class
    crawlers = list()
    for crawler_type in crawler_module.__dict__.values():
        if crawler_type is not cutils.TyreCrawler and isinstance(crawler_type, type) and issubclass(crawler_type, cutils.TyreCrawler):
            crawlers.append(crawler_type)

    # Check if there is only one crawler
    return crawlers
