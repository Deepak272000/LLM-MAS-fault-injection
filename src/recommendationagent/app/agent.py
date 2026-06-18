import importlib
from app.grpc_client import RecommendationGrpcClient
import app.fault_injection as fi

client = RecommendationGrpcClient()


class RecommendationAgent:
    def _fetch(self, user_id: str, product_ids: list[str], action: str) -> dict:
        fi.clear_lkw()
        fi.record_checkpoint("TASK_START", {
            "user_id": user_id,
            "product_ids": product_ids,
            "action": action,
            "fault_mode": fi.FAULT_MODE,
        })

        # FM_3_1: premature termination
        early = fi.maybe_premature_termination()
        if early is not None:
            fi.record_checkpoint("FINAL_ANSWER", {"premature_termination": True})
            return {"mode": "agent", "action": action, "user_id": user_id,
                    "input_product_ids": product_ids, "recommended_product_ids": early,
                    "lkw": fi.get_lkw()}

        # FM_2_5: swap user_id
        user_id, user_id_swapped = fi.maybe_swap_user_id(user_id)

        recommended_ids = client.list_recommendations(
            user_id=user_id,
            product_ids=product_ids,
        )

        # FM_2_2: hallucinate IDs
        recommended_ids, hallucinated = fi.maybe_hallucinate_recs(recommended_ids)
        # BL_EMPTY_RECS
        recommended_ids, empty_recs = fi.maybe_empty_recs(recommended_ids)
        # BL_SELF_RECOMMENDATION
        recommended_ids, self_rec = fi.maybe_self_recommendation(recommended_ids, product_ids)
        # BL_INJECTION_RECS
        recommended_ids, injection = fi.maybe_inject_sponsored(recommended_ids)
        # BL_SHUFFLED_RECS
        recommended_ids, shuffled = fi.maybe_shuffle_recs(recommended_ids)

        fi.record_checkpoint("RECOMMEND_DONE", {
            "action": action,
            "count": len(recommended_ids),
            "hallucinated": hallucinated,
            "user_id_swapped": user_id_swapped,
            "method_swapped": fi.FAULT_MODE == "FM_1_2",
            "empty_recs": empty_recs,
            "self_rec": self_rec,
            "injection": injection,
            "shuffled": shuffled,
        })
        fi.record_checkpoint("FINAL_ANSWER", {"count": len(recommended_ids)})

        return {
            "mode": "agent",
            "action": action,
            "user_id": user_id,
            "input_product_ids": product_ids,
            "recommended_product_ids": recommended_ids,
            "lkw": fi.get_lkw(),
        }

    def get_recommendations(self, user_id: str, product_ids: list[str]) -> dict:
        """Fetch recommended product IDs for a user given their current product context."""
        action = "get_recommendations"
        if fi.FAULT_MODE == "FM_1_2":
            action = "explain_recommendations"
        return self._fetch(user_id, product_ids, action)

    def explain_recommendations(self, user_id: str, product_ids: list[str]) -> dict:
        """
        Fetch recommendations and return raw data so the LLM node can
        generate a human-readable explanation downstream.
        """
        action = "explain_recommendations"
        if fi.FAULT_MODE == "FM_1_2":
            action = "get_recommendations"
        return self._fetch(user_id, product_ids, action)