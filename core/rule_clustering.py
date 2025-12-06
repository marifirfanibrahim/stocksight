"""
rule clustering module
groups skus using business rules not statistical clustering
uses volume tiers and pattern types
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

import config


# ============================================================================
#                               DATA CLASSES
# ============================================================================

@dataclass
class SKUCluster:
    # cluster information for single sku
    sku: str
    volume_tier: str      # A B or C
    pattern_type: str     # seasonal erratic variable steady
    total_volume: float
    cv: float             # coefficient of variation
    q4_concentration: float
    cluster_label: str


# ============================================================================
#                             RULE CLUSTERING
# ============================================================================

class RuleClustering:
    # rule based clustering using volume and pattern thresholds
    
    def __init__(self, use_percentiles: bool = True):
        # initialize with clustering configuration
        self.config = config.CLUSTERING
        self.use_percentiles = use_percentiles
        self.sku_clusters = {}
        self.cluster_summary = {}
    
    # ---------- MAIN CLUSTERING ----------
    
    def cluster_skus(self, 
                     df: pd.DataFrame, 
                     sku_col: str, 
                     date_col: str, 
                     qty_col: str) -> Dict[str, SKUCluster]:
        # cluster all skus using rule based approach
        
        # calculate metrics for each sku
        sku_metrics = self._calculate_sku_metrics(df, sku_col, date_col, qty_col)
        
        # determine volume thresholds
        if self.use_percentiles:
            volume_thresholds = self._calculate_percentile_thresholds(sku_metrics)
        else:
            volume_thresholds = self.config["volume_thresholds"]
        
        # assign clusters
        for sku, metrics in sku_metrics.items():
            volume_tier = self._assign_volume_tier(metrics["total_volume"], volume_thresholds)
            pattern_type = self._assign_pattern_type(metrics["cv"], metrics["q4_concentration"])
            
            cluster_label = config.get_cluster_label(volume_tier, pattern_type)
            
            self.sku_clusters[sku] = SKUCluster(
                sku=sku,
                volume_tier=volume_tier,
                pattern_type=pattern_type,
                total_volume=metrics["total_volume"],
                cv=metrics["cv"],
                q4_concentration=metrics["q4_concentration"],
                cluster_label=cluster_label
            )
        
        # calculate summary
        self._calculate_cluster_summary()
        
        return self.sku_clusters
    
    def _calculate_sku_metrics(self, 
                               df: pd.DataFrame, 
                               sku_col: str, 
                               date_col: str, 
                               qty_col: str) -> Dict[str, Dict]:
        # calculate clustering metrics for each sku
        metrics = {}
        
        # group by sku
        for sku, group in df.groupby(sku_col):
            total_volume = group[qty_col].sum()
            mean_volume = group[qty_col].mean()
            std_volume = group[qty_col].std()
            
            # coefficient of variation
            cv = std_volume / mean_volume if mean_volume > 0 else 0
            
            # q4 concentration for seasonality detection
            group_with_month = group.copy()
            group_with_month["month"] = pd.to_datetime(group[date_col]).dt.month
            q4_volume = group_with_month[group_with_month["month"].isin([10, 11, 12])][qty_col].sum()
            q4_concentration = q4_volume / total_volume if total_volume > 0 else 0
            
            metrics[sku] = {
                "total_volume": total_volume,
                "mean_volume": mean_volume,
                "std_volume": std_volume,
                "cv": cv,
                "q4_concentration": q4_concentration,
                "data_points": len(group)
            }
        
        return metrics
    
    def _calculate_percentile_thresholds(self, sku_metrics: Dict) -> Dict[str, float]:
        # calculate volume thresholds based on percentiles
        volumes = [m["total_volume"] for m in sku_metrics.values()]
        volumes_sorted = sorted(volumes, reverse=True)
        
        n = len(volumes_sorted)
        a_percentile = self.config["volume_percentiles"]["A"]
        b_percentile = self.config["volume_percentiles"]["B"]
        
        # find threshold values
        a_idx = int(n * (100 - a_percentile) / 100)
        b_idx = int(n * (100 - b_percentile) / 100)
        
        return {
            "A": volumes_sorted[min(a_idx, n - 1)],
            "B": volumes_sorted[min(b_idx, n - 1)],
            "C": 0
        }
    
    def _assign_volume_tier(self, volume: float, thresholds: Dict[str, float]) -> str:
        # assign volume tier based on thresholds
        if volume >= thresholds["A"]:
            return "A"
        elif volume >= thresholds["B"]:
            return "B"
        else:
            return "C"
    
    def _assign_pattern_type(self, cv: float, q4_concentration: float) -> str:
        # assign pattern type based on metrics
        thresholds = self.config["pattern_thresholds"]
        
        # check for strong seasonality first
        if q4_concentration >= thresholds["seasonal"]:
            return "seasonal"
        
        # check volatility
        if cv >= thresholds["erratic"]:
            return "erratic"
        elif cv >= thresholds["variable"]:
            return "variable"
        else:
            return "steady"
    
    # ---------- CLUSTER SUMMARY ----------
    
    def _calculate_cluster_summary(self) -> None:
        # calculate summary statistics for each cluster
        self.cluster_summary = {}
        
        # group by volume tier and pattern type
        for cluster in self.sku_clusters.values():
            key = (cluster.volume_tier, cluster.pattern_type)
            
            if key not in self.cluster_summary:
                self.cluster_summary[key] = {
                    "volume_tier": cluster.volume_tier,
                    "pattern_type": cluster.pattern_type,
                    "label": cluster.cluster_label,
                    "sku_count": 0,
                    "total_volume": 0,
                    "skus": []
                }
            
            self.cluster_summary[key]["sku_count"] += 1
            self.cluster_summary[key]["total_volume"] += cluster.total_volume
            self.cluster_summary[key]["skus"].append(cluster.sku)
    
    def get_cluster_summary(self) -> List[Dict]:
        # get cluster summary as list
        summary = []
        
        for key, data in self.cluster_summary.items():
            summary.append({
                "cluster": data["label"],
                "volume_tier": data["volume_tier"],
                "pattern_type": data["pattern_type"],
                "item_count": data["sku_count"],
                "total_volume": data["total_volume"],
                "pct_of_items": 0,  # calculated after
                "pct_of_volume": 0  # calculated after
            })
        
        # calculate percentages
        total_items = sum(s["item_count"] for s in summary)
        total_volume = sum(s["total_volume"] for s in summary)
        
        for s in summary:
            s["pct_of_items"] = (s["item_count"] / total_items * 100) if total_items > 0 else 0
            s["pct_of_volume"] = (s["total_volume"] / total_volume * 100) if total_volume > 0 else 0
        
        # sort by volume tier then pattern
        tier_order = {"A": 0, "B": 1, "C": 2}
        summary.sort(key=lambda x: (tier_order.get(x["volume_tier"], 3), x["pattern_type"]))
        
        return summary
    
    # ---------- FILTERING ----------
    
    def get_skus_by_tier(self, tier: str) -> List[str]:
        # get all skus in volume tier
        return [c.sku for c in self.sku_clusters.values() if c.volume_tier == tier]
    
    def get_skus_by_pattern(self, pattern: str) -> List[str]:
        # get all skus with pattern type
        return [c.sku for c in self.sku_clusters.values() if c.pattern_type == pattern]
    
    def get_skus_by_cluster(self, tier: str, pattern: str) -> List[str]:
        # get skus matching both tier and pattern
        return [
            c.sku for c in self.sku_clusters.values() 
            if c.volume_tier == tier and c.pattern_type == pattern
        ]
    
    def get_cluster_for_sku(self, sku: str) -> Optional[SKUCluster]:
        # get cluster info for single sku
        return self.sku_clusters.get(sku)
    
    # ---------- THRESHOLD ADJUSTMENT ----------
    
    def update_volume_thresholds(self, new_thresholds: Dict[str, float]) -> None:
        # update volume thresholds
        self.config["volume_thresholds"] = new_thresholds
        self.use_percentiles = False
    
    def update_pattern_thresholds(self, new_thresholds: Dict[str, float]) -> None:
        # update pattern thresholds
        self.config["pattern_thresholds"] = new_thresholds
    
    # ---------- EXPORT ----------
    
    def get_cluster_matrix(self) -> pd.DataFrame:
        # create cluster matrix for display
        tiers = ["A", "B", "C"]
        patterns = ["seasonal", "erratic", "variable", "steady"]
        
        matrix_data = []
        for tier in tiers:
            row = {"volume_tier": tier}
            for pattern in patterns:
                key = (tier, pattern)
                if key in self.cluster_summary:
                    row[pattern] = self.cluster_summary[key]["sku_count"]
                else:
                    row[pattern] = 0
            matrix_data.append(row)
        
        return pd.DataFrame(matrix_data).set_index("volume_tier")
    
    def export_clusters(self) -> pd.DataFrame:
        # export cluster assignments as dataframe
        data = []
        for sku, cluster in self.sku_clusters.items():
            data.append({
                "sku": sku,
                "volume_tier": cluster.volume_tier,
                "pattern_type": cluster.pattern_type,
                "cluster": cluster.cluster_label,
                "total_volume": cluster.total_volume,
                "cv": cluster.cv,
                "q4_concentration": cluster.q4_concentration
            })
        
        return pd.DataFrame(data)