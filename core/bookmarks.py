"""
bookmark management system
save and organize skus, anomaly sets, forecasts
"""


# ================ IMPORTS ================

import json
import threading
from typing import Callable, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from core.state import STATE, Bookmark
from config import Paths


# ================ BOOKMARK TYPES ================

class BookmarkType:
    """
    bookmark type constants
    """
    SKU = 'sku'
    ANOMALY_SET = 'anomaly_set'
    FORECAST = 'forecast'
    FEATURE_SET = 'feature_set'
    FILTER = 'filter'


# ================ BOOKMARK MANAGER ================

class BookmarkManager:
    """
    centralized bookmark management
    """
    
    def __init__(self):
        # ---------- CALLBACKS ----------
        self._callbacks: List[Callable] = []
        
        # ---------- LOCK ----------
        self._lock = threading.RLock()
        
        # ---------- LOAD PERSISTED BOOKMARKS ----------
        self._load_bookmarks()
    
    # ================ BOOKMARK CREATION ================
    
    def create(
        self,
        name: str,
        bookmark_type: str,
        items: List[str],
        notes: str = ""
    ) -> str:
        """
        create new bookmark
        """
        with self._lock:
            bookmark_id = STATE.add_bookmark(
                name=name,
                bookmark_type=bookmark_type,
                items=items,
                notes=notes
            )
            
            self._notify_callbacks('created', bookmark_id)
            self._save_bookmarks()
            
            return bookmark_id
    
    def bookmark_sku(self, sku: str, notes: str = "") -> str:
        """
        bookmark single sku
        """
        return self.create(
            name=f"SKU: {sku}",
            bookmark_type=BookmarkType.SKU,
            items=[sku],
            notes=notes
        )
    
    def bookmark_skus(self, name: str, skus: List[str], notes: str = "") -> str:
        """
        bookmark multiple skus
        """
        return self.create(
            name=name,
            bookmark_type=BookmarkType.SKU,
            items=skus,
            notes=notes
        )
    
    def bookmark_anomalies(self, name: str, anomaly_ids: List[str], notes: str = "") -> str:
        """
        bookmark anomaly set
        """
        return self.create(
            name=name,
            bookmark_type=BookmarkType.ANOMALY_SET,
            items=anomaly_ids,
            notes=notes
        )
    
    def bookmark_forecast(self, name: str, forecast_id: str, notes: str = "") -> str:
        """
        bookmark forecast result
        """
        return self.create(
            name=name,
            bookmark_type=BookmarkType.FORECAST,
            items=[forecast_id],
            notes=notes
        )
    
    def bookmark_features(self, name: str, feature_names: List[str], notes: str = "") -> str:
        """
        bookmark feature set
        """
        return self.create(
            name=name,
            bookmark_type=BookmarkType.FEATURE_SET,
            items=feature_names,
            notes=notes
        )
    
    # ================ BOOKMARK MANAGEMENT ================
    
    def update(self, bookmark_id: str, name: str = None, items: List[str] = None, notes: str = None):
        """
        update existing bookmark
        """
        with self._lock:
            for bookmark in STATE.bookmarks:
                if bookmark.id == bookmark_id:
                    if name is not None:
                        bookmark.name = name
                    if items is not None:
                        bookmark.items = items
                    if notes is not None:
                        bookmark.notes = notes
                    
                    self._notify_callbacks('updated', bookmark_id)
                    self._save_bookmarks()
                    return True
            
            return False
    
    def delete(self, bookmark_id: str):
        """
        delete bookmark by id
        """
        with self._lock:
            STATE.remove_bookmark(bookmark_id)
            self._notify_callbacks('deleted', bookmark_id)
            self._save_bookmarks()
    
    def delete_by_type(self, bookmark_type: str):
        """
        delete all bookmarks of specific type
        """
        with self._lock:
            STATE.bookmarks = [b for b in STATE.bookmarks if b.bookmark_type != bookmark_type]
            self._notify_callbacks('deleted_type', bookmark_type)
            self._save_bookmarks()
    
    def clear_all(self):
        """
        delete all bookmarks
        """
        with self._lock:
            STATE.bookmarks = []
            self._notify_callbacks('cleared', None)
            self._save_bookmarks()
    
    # ================ QUERIES ================
    
    def get(self, bookmark_id: str) -> Optional[Bookmark]:
        """
        get bookmark by id
        """
        with self._lock:
            for bookmark in STATE.bookmarks:
                if bookmark.id == bookmark_id:
                    return bookmark
            return None
    
    def get_all(self) -> List[Bookmark]:
        """
        get all bookmarks
        """
        return STATE.get_bookmarks()
    
    def get_by_type(self, bookmark_type: str) -> List[Bookmark]:
        """
        get bookmarks by type
        """
        return STATE.get_bookmarks(bookmark_type)
    
    def get_sku_bookmarks(self) -> List[Bookmark]:
        """
        get all sku bookmarks
        """
        return self.get_by_type(BookmarkType.SKU)
    
    def get_anomaly_bookmarks(self) -> List[Bookmark]:
        """
        get all anomaly set bookmarks
        """
        return self.get_by_type(BookmarkType.ANOMALY_SET)
    
    def get_forecast_bookmarks(self) -> List[Bookmark]:
        """
        get all forecast bookmarks
        """
        return self.get_by_type(BookmarkType.FORECAST)
    
    def get_feature_bookmarks(self) -> List[Bookmark]:
        """
        get all feature set bookmarks
        """
        return self.get_by_type(BookmarkType.FEATURE_SET)
    
    def search(self, query: str) -> List[Bookmark]:
        """
        search bookmarks by name or notes
        """
        query_lower = query.lower()
        
        with self._lock:
            results = []
            
            for bookmark in STATE.bookmarks:
                if query_lower in bookmark.name.lower():
                    results.append(bookmark)
                elif query_lower in bookmark.notes.lower():
                    results.append(bookmark)
                elif any(query_lower in item.lower() for item in bookmark.items):
                    results.append(bookmark)
            
            return results
    
    def is_bookmarked(self, item: str, bookmark_type: str = None) -> bool:
        """
        check if item is bookmarked
        """
        with self._lock:
            for bookmark in STATE.bookmarks:
                if bookmark_type and bookmark.bookmark_type != bookmark_type:
                    continue
                if item in bookmark.items:
                    return True
            return False
    
    def get_count(self) -> int:
        """
        get total bookmark count
        """
        return len(STATE.bookmarks)
    
    def get_count_by_type(self) -> Dict[str, int]:
        """
        get bookmark counts by type
        """
        counts = {}
        
        with self._lock:
            for bookmark in STATE.bookmarks:
                bt = bookmark.bookmark_type
                counts[bt] = counts.get(bt, 0) + 1
        
        return counts
    
    # ================ CALLBACKS ================
    
    def add_callback(self, callback: Callable):
        """
        add callback for bookmark changes
        callback receives action type and bookmark_id
        """
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """
        remove callback
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, action: str, bookmark_id: Optional[str]):
        """
        notify all callbacks
        """
        for callback in self._callbacks:
            try:
                callback(action, bookmark_id)
            except Exception as e:
                print(f"bookmark callback error: {e}")
    
    # ================ PERSISTENCE ================
    
    def _save_bookmarks(self):
        """
        save bookmarks to file
        """
        try:
            bookmarks_data = []
            
            for bookmark in STATE.bookmarks:
                bookmarks_data.append({
                    'id': bookmark.id,
                    'name': bookmark.name,
                    'bookmark_type': bookmark.bookmark_type,
                    'items': bookmark.items,
                    'created_at': bookmark.created_at.isoformat(),
                    'notes': bookmark.notes
                })
            
            Paths.DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(Paths.BOOKMARKS_FILE, 'w') as f:
                json.dump(bookmarks_data, f, indent=2)
                
        except Exception as e:
            print(f"error saving bookmarks: {e}")
    
    def _load_bookmarks(self):
        """
        load bookmarks from file
        """
        try:
            if not Paths.BOOKMARKS_FILE.exists():
                return
            
            with open(Paths.BOOKMARKS_FILE, 'r') as f:
                bookmarks_data = json.load(f)
            
            STATE.bookmarks = []
            
            for data in bookmarks_data:
                bookmark = Bookmark(
                    id=data['id'],
                    name=data['name'],
                    bookmark_type=data['bookmark_type'],
                    items=data['items'],
                    created_at=datetime.fromisoformat(data['created_at']),
                    notes=data.get('notes', '')
                )
                STATE.bookmarks.append(bookmark)
                
        except Exception as e:
            print(f"error loading bookmarks: {e}")
    
    # ================ EXPORT/IMPORT ================
    
    def export_to_dict(self) -> List[Dict]:
        """
        export bookmarks as list of dicts
        """
        with self._lock:
            return [
                {
                    'name': b.name,
                    'type': b.bookmark_type,
                    'items': b.items,
                    'notes': b.notes,
                    'created_at': b.created_at.isoformat()
                }
                for b in STATE.bookmarks
            ]
    
    def import_from_dict(self, bookmarks_data: List[Dict]):
        """
        import bookmarks from list of dicts
        """
        with self._lock:
            for data in bookmarks_data:
                self.create(
                    name=data['name'],
                    bookmark_type=data['type'],
                    items=data['items'],
                    notes=data.get('notes', '')
                )


# ================ SINGLETON INSTANCE ================

BOOKMARKS = BookmarkManager()