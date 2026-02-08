// static/js/reactions.js
(() => {
  "use strict";

  function getCookie(name) {
    const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  }

  async function toggleReaction(btn) {
    const payload = {
      app_label: btn.dataset.app,
      model: btn.dataset.model,
      object_id: btn.dataset.objectId,
      reaction_type: btn.dataset.reaction,
    };

    // 必須キーが欠けてたら早期リターン（400回避・原因特定しやすい）
    if (!payload.app_label || !payload.model || !payload.object_id || !payload.reaction_type) {
      console.error("Reaction payload is missing:", payload, btn);
      alert("設定が不足しています（data-* が足りません）");
      return;
    }

    const res = await fetch("/reactions/toggle/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      // 401/403/400 など
      alert("ログインが必要か、エラーが発生しました");
      return;
    }

    const data = await res.json();

    // count更新
    const countEl = btn.querySelector(".js-count");
    if (countEl && typeof data.count !== "undefined") {
      countEl.textContent = data.count;
    }

    // activeでopacity更新
    if (typeof data.active !== "undefined") {
      btn.style.opacity = data.active ? "1.0" : "0.6";
    }
  }

  function bind(container = document) {
    container.querySelectorAll(".js-react").forEach((btn) => {
      if (btn.dataset.bound === "1") return; // 二重bind防止
      btn.dataset.bound = "1";

      btn.addEventListener("click", () => toggleReaction(btn));
    });
  }

  // 初期bind
  document.addEventListener("DOMContentLoaded", () => bind());

  // 他のJSから再bindしたいとき用（AJAXでボタン追加とか）
  window.bindReactions = bind;
})();
