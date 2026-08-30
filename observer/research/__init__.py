from observer.research.base import ResearchAdapter
from observer.research.corporate import CorporateRegistriesAdapter
from observer.research.court import CourtRecordsAdapter
from observer.research.http_fetch import HttpFetchAdapter
from observer.research.patents import PatentsAdapter
from observer.research.procurement import ProcurementAdapter
from observer.research.sec import SecFilingsAdapter
from observer.research.unavailable import UNAVAILABLE_ADAPTERS
from observer.research.url_intake import UrlIntakeAdapter
from observer.research.wayback import WaybackAdapter
from observer.research.web_search import WebSearchAdapter

__all__ = [
    "ResearchAdapter",
    "HttpFetchAdapter",
    "UrlIntakeAdapter",
    "WebSearchAdapter",
    "WaybackAdapter",
    "CourtRecordsAdapter",
    "CorporateRegistriesAdapter",
    "SecFilingsAdapter",
    "PatentsAdapter",
    "ProcurementAdapter",
    "UNAVAILABLE_ADAPTERS",
]
