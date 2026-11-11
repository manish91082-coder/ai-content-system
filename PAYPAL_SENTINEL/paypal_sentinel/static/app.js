let currentPlan = null;
let approvalToken = null;
let paypalLoaded = false;

async function api(path, body) {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? {"Content-Type":"application/json"} : {},
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function setStatus(message) {
  document.getElementById("status").textContent = message;
}

function renderPlan(plan) {
  const result = document.getElementById("result");
  result.classList.remove("hidden");
  const decision = document.getElementById("decision");
  decision.textContent = plan.decision;
  decision.className = "decision " + plan.decision.toLowerCase();
  document.getElementById("details").innerHTML =
    '<div class="detail-grid">' +
    '<div class="metric"><small>Product</small><strong>' + escapeHtml(plan.item_name) + '</strong></div>' +
    '<div class="metric"><small>Quantity</small><strong>' + plan.quantity + '</strong></div>' +
    '<div class="metric"><small>Verified amount</small><strong>' + plan.currency + ' ' + plan.amount + '</strong></div>' +
    '</div>';
  document.getElementById("rationale").textContent = "AI rationale: " + plan.rationale;
  document.getElementById("reasons").textContent = "Policy evidence: " + plan.reasons.join(", ");
  document.getElementById("approve").classList.toggle("hidden", plan.decision !== "WARN");
  document.getElementById("paypal-button-container").innerHTML = "";
  setStatus(plan.decision === "BLOCK" ? "Blocked before any PayPal order was created." :
    plan.decision === "WARN" ? "Human approval is required before checkout." :
    "Policy allows this intent. Continue to PayPal sandbox checkout.");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, function(ch) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch];
  });
}

async function loadPayPalButton() {
  if (!currentPlan || currentPlan.decision === "BLOCK") return;
  const config = await api("/api/config");
  if (!config.paypal_client_id) {
    setStatus("Add your PayPal sandbox client ID to the server environment to enable checkout.");
    return;
  }
  if (!paypalLoaded) {
    await new Promise(function(resolve, reject) {
      const script = document.createElement("script");
      script.src = "https://www.paypal.com/sdk/js?client-id=" + encodeURIComponent(config.paypal_client_id) + "&components=buttons&currency=USD&intent=capture";
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
    paypalLoaded = true;
  }
  window.paypal.Buttons({
    createOrder: async function() {
      const order = await api("/api/paypal/orders", {
        plan_id: currentPlan.plan_id,
        approval_token: approvalToken
      });
      approvalToken = null;
      return order.id;
    },
    onApprove: async function(data) {
      setStatus("Buyer approved. Verifying capture with PayPal sandbox...");
      const captured = await api("/api/paypal/orders/" + encodeURIComponent(data.orderID) + "/capture", {});
      setStatus("PayPal sandbox reports " + captured.status + ". Capture ID: " + captured.capture_id);
    },
    onError: function(error) {
      setStatus("PayPal checkout error: " + error.message);
    }
  }).render("#paypal-button-container");
}

document.getElementById("analyse").addEventListener("click", async function() {
  const button = this;
  button.disabled = true;
  setStatus("Gemini is parsing the request and checking risk...");
  try {
    currentPlan = await api("/api/agent/plan", {prompt: document.getElementById("prompt").value});
    approvalToken = null;
    renderPlan(currentPlan);
    if (currentPlan.decision === "ALLOW") await loadPayPalButton();
  } catch (error) {
    setStatus(error.message);
  } finally {
    button.disabled = false;
  }
});

document.getElementById("approve").addEventListener("click", async function() {
  if (!currentPlan) return;
  this.disabled = true;
  try {
    const result = await api("/api/agent/approve", {plan_id: currentPlan.plan_id});
    approvalToken = result.approval_token;
    setStatus("Exact purchase approved once. You must still approve payment in PayPal.");
    await loadPayPalButton();
  } catch (error) {
    setStatus(error.message);
  } finally {
    this.disabled = false;
  }
});
