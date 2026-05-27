"""
Agency Dashboard — Streamlit app showing live revenue, leads, clients, and
delivered services. Run with: streamlit run agency/dashboard.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime

from agency.db.models import init_db, get_leads, get_clients, get_conn
from agency.revenue.tracker import get_revenue_summary
from agency.config import cfg, NICHES, PACKAGES

st.set_page_config(
    page_title=f"{cfg.agency_name} — Dashboard",
    page_icon="🤖",
    layout="wide",
)

# Init DB on first load
init_db()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title(f"🤖 {cfg.agency_name}")
    st.caption("Hands-free AI automation agency")
    st.divider()

    page = st.radio(
        "Navigate",
        ["Revenue", "Leads", "Clients", "Opportunities", "Onboard Client", "Services"],
        index=0,
    )
    st.divider()

    if st.button("Run All Tasks Now", use_container_width=True):
        with st.spinner("Running all automation tasks..."):
            from agency.leads.finder import run_lead_discovery
            from agency.leads.scorer import qualify_leads
            from agency.niches.researcher import run_niche_research
            run_lead_discovery()
            qualify_leads()
            run_niche_research()
        st.success("Tasks complete!")

    if st.button("Send Outreach Now", use_container_width=True):
        with st.spinner("Sending emails..."):
            from agency.outreach.email_sender import run_outreach
            n = run_outreach()
        st.success(f"{n} emails sent!")


# ── Revenue Page ──────────────────────────────────────────────────────────────
if page == "Revenue":
    st.title("Revenue Dashboard")

    summary = get_revenue_summary()
    target = cfg.weekly_revenue_target

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Monthly Recurring Revenue", f"${summary['mrr']:,.2f}", delta=f"${summary['mrr']/4.33:,.0f}/wk equiv")
    col2.metric("This Week's Revenue", f"${summary['weekly_revenue']:,.2f}", delta=f"{summary['weekly_pct_of_target']:.0f}% of ${target:,.0f} target")
    col3.metric("Total Revenue (All Time)", f"${summary['total_revenue']:,.2f}")
    col4.metric("Annual Run Rate", f"${summary['arr']:,.2f}")

    st.divider()
    col5, col6, col7 = st.columns(3)
    col5.metric("Active Clients", summary["active_clients"])
    col6.metric("In Pipeline (Onboarding)", summary["pipeline_clients"])
    col7.metric("Total Leads", summary["total_leads"])

    st.subheader("Weekly Revenue — Last 8 Weeks")
    if summary["weekly_history"]:
        df = pd.DataFrame(summary["weekly_history"])
        df["week_label"] = df["week"].apply(lambda x: f"W-{8-x}")
        st.bar_chart(df.set_index("week_label")["amount"])

    st.subheader("Revenue by Type")
    if summary["revenue_by_type"]:
        df2 = pd.DataFrame(
            [{"Type": k, "Amount": v} for k, v in summary["revenue_by_type"].items()]
        )
        st.dataframe(df2, use_container_width=True)

    st.subheader("Path to $1,000/week")
    months_left = summary["months_to_target"]
    if months_left == 0:
        st.success("Target reached!")
    else:
        progress = min(summary["weekly_revenue"] / target, 1.0)
        st.progress(progress, text=f"${summary['weekly_revenue']:,.2f} / ${target:,.0f} per week")
        st.info(
            f"At current growth pace (~1 new client/month), you'll hit ${target:,.0f}/week "
            f"in approximately **{months_left:.1f} months**. "
            f"Need {summary['active_clients']} → ~{int(target*4.33/350)} active clients."
        )

    st.subheader("Log Manual Revenue")
    with st.form("manual_rev"):
        amount = st.number_input("Amount ($)", min_value=0.0, value=0.0)
        rev_type = st.selectbox("Type", ["setup_fee", "mrr", "bonus", "other"])
        desc = st.text_input("Description")
        submitted = st.form_submit_button("Log Revenue")
        if submitted and amount > 0:
            from agency.revenue.tracker import log_manual_revenue
            log_manual_revenue(amount, rev_type, desc)
            st.success(f"Logged ${amount:.2f}")
            st.rerun()


# ── Leads Page ────────────────────────────────────────────────────────────────
elif page == "Leads":
    st.title("Lead Pipeline")

    conn = get_conn()
    df_raw = pd.read_sql_query("SELECT * FROM leads ORDER BY score DESC", conn)
    conn.close()

    if df_raw.empty:
        st.info("No leads yet. Click 'Run All Tasks Now' in the sidebar to discover leads.")
    else:
        status_counts = df_raw["status"].value_counts()
        cols = st.columns(len(status_counts))
        for i, (status, cnt) in enumerate(status_counts.items()):
            cols[i].metric(status.replace("_", " ").title(), cnt)

        st.divider()

        status_filter = st.multiselect(
            "Filter by status",
            df_raw["status"].unique().tolist(),
            default=["qualified", "contacted"],
        )
        filtered = df_raw[df_raw["status"].isin(status_filter)] if status_filter else df_raw

        display_cols = ["business_name", "niche", "city", "rating", "review_count", "score", "status", "email"]
        st.dataframe(
            filtered[display_cols].rename(columns=str.title),
            use_container_width=True,
        )

        st.caption(f"Showing {len(filtered)} of {len(df_raw)} leads")

        # Manually add email for a lead
        st.subheader("Add Email to Lead")
        with st.form("add_email"):
            lead_id = st.number_input("Lead ID", min_value=1, step=1)
            email_input = st.text_input("Email address")
            if st.form_submit_button("Save Email"):
                from agency.db.models import update_lead
                update_lead(int(lead_id), {"email": email_input})
                st.success("Email saved!")
                st.rerun()


# ── Clients Page ──────────────────────────────────────────────────────────────
elif page == "Clients":
    st.title("Active Clients")

    conn = get_conn()
    df_clients = pd.read_sql_query("SELECT * FROM clients ORDER BY created_at DESC", conn)
    df_services = pd.read_sql_query(
        "SELECT * FROM services_delivered ORDER BY delivered_at DESC", conn
    )
    conn.close()

    if df_clients.empty:
        st.info("No clients yet. Use the Onboard Client page to add your first client.")
    else:
        display = ["business_name", "niche", "plan", "mrr", "setup_fee", "status", "onboarded_at", "email"]
        st.dataframe(df_clients[display].rename(columns=str.title), use_container_width=True)

        st.subheader("Services Delivered")
        if not df_services.empty:
            st.dataframe(
                df_services[["client_id", "service_type", "title", "delivered_at", "status"]],
                use_container_width=True,
            )
        else:
            st.info("No services delivered yet.")

        # View a service delivery
        if not df_services.empty:
            sel = st.selectbox(
                "View service content",
                df_services["id"].tolist(),
                format_func=lambda x: df_services[df_services["id"] == x]["title"].iloc[0],
            )
            row = df_services[df_services["id"] == sel].iloc[0]
            st.text_area("Content", row["content"], height=300)


# ── Opportunities Page ─────────────────────────────────────────────────────────
elif page == "Opportunities":
    st.title("Niche Opportunities (Upwork/Fiverr)")

    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM niche_opportunities ORDER BY score DESC LIMIT 50", conn
    )
    conn.close()

    if df.empty:
        st.info("No opportunities scanned yet. Click 'Run All Tasks Now' to research.")
    else:
        st.dataframe(
            df[["platform", "title", "score", "budget_min", "url", "found_at"]],
            use_container_width=True,
        )

        sel_id = st.selectbox("Generate pitch for opportunity", df["id"].tolist(),
                              format_func=lambda x: df[df["id"]==x]["title"].iloc[0])
        if st.button("Generate AI Pitch"):
            row = df[df["id"] == sel_id].iloc[0]
            with st.spinner("Writing pitch..."):
                from agency.niches.researcher import analyze_opportunity_with_ai
                pitch = analyze_opportunity_with_ai(row.to_dict())
            st.text_area("Pitch Opener", pitch, height=150)
            conn2 = get_conn()
            conn2.execute("UPDATE niche_opportunities SET acted_on=1 WHERE id=?", (sel_id,))
            conn2.commit()
            conn2.close()


# ── Onboard Client Page ───────────────────────────────────────────────────────
elif page == "Onboard Client":
    st.title("Onboard New Client")
    st.caption("Fill in client details — the system handles welcome email, service delivery, and billing automatically.")

    with st.form("onboard"):
        col1, col2 = st.columns(2)
        biz_name = col1.text_input("Business Name *")
        contact_name = col2.text_input("Contact Name")
        email = col1.text_input("Email *")
        phone = col2.text_input("Phone")
        niche = col1.selectbox("Niche", [n.name.replace("_", " ") for n in NICHES])
        city = col2.text_input("City")
        plan = st.selectbox(
            "Package",
            list(PACKAGES.keys()),
            format_func=lambda p: f"{PACKAGES[p]['name']} — ${PACKAGES[p]['setup_fee']} setup + ${PACKAGES[p]['mrr']}/mo",
        )
        st.write("**Deliverables:**")
        for d in PACKAGES[plan]["deliverables"]:
            st.write(f"• {d}")

        lead_id = st.number_input("Lead ID (if from pipeline, else 0)", min_value=0, step=1)
        submitted = st.form_submit_button("Onboard Client", use_container_width=True)

        if submitted:
            if not biz_name or not email:
                st.error("Business name and email are required.")
            else:
                from agency.onboarding.pipeline import onboard_client
                with st.spinner("Onboarding client..."):
                    cid = onboard_client(
                        lead_id=int(lead_id),
                        business_name=biz_name,
                        contact_name=contact_name,
                        email=email,
                        phone=phone,
                        niche=niche.replace(" ", "_"),
                        plan=plan,
                        city=city,
                    )
                st.success(f"Client onboarded! ID: {cid}")
                pkg = PACKAGES[plan]
                st.balloons()
                st.info(
                    f"Revenue logged: ${pkg['setup_fee']} setup + ${pkg['mrr']}/mo MRR. "
                    f"Welcome email queued. Services being delivered."
                )


# ── Services Page ─────────────────────────────────────────────────────────────
elif page == "Services":
    st.title("Service Delivery Controls")

    clients = get_clients(status="active") + get_clients(status="onboarding")
    if not clients:
        st.info("No clients to deliver services to yet.")
    else:
        client_names = {c["id"]: c["business_name"] for c in clients}
        sel_client_id = st.selectbox(
            "Select Client",
            list(client_names.keys()),
            format_func=lambda x: client_names[x],
        )
        sel_client = next(c for c in clients if c["id"] == sel_client_id)

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Generate Chatbot Config", use_container_width=True):
                from agency.services.chatbot_builder import deliver_chatbot_service
                with st.spinner("Building chatbot..."):
                    deliver_chatbot_service(sel_client)
                st.success("Chatbot config generated and logged!")

        with col2:
            if st.button("Generate Review Sequences", use_container_width=True):
                from agency.services.review_agent import deliver_review_service
                with st.spinner("Writing sequences..."):
                    deliver_review_service(sel_client)
                st.success("Review sequences generated!")

        with col3:
            if st.button("Generate SEO Content", use_container_width=True):
                from agency.services.content_agent import deliver_content_service
                with st.spinner("Writing content..."):
                    deliver_content_service(sel_client)
                st.success("SEO content generated!")

        if st.button("Send Monthly Report Now", use_container_width=True):
            from agency.reporting.client_report import generate_report, send_email
            with st.spinner("Generating report..."):
                report = generate_report(sel_client)
            st.text_area("Report Preview", report, height=400)
            if st.button("Send Report Email"):
                from agency.outreach.email_sender import send_email
                send_email(
                    sel_client["email"],
                    f"Your Monthly Report — {cfg.agency_name}",
                    report,
                )
                st.success("Report sent!")

    st.divider()
    st.subheader("Pricing Packages")
    for k, pkg in PACKAGES.items():
        with st.expander(f"{pkg['name']} — ${pkg['setup_fee']} setup + ${pkg['mrr']}/mo"):
            for d in pkg["deliverables"]:
                st.write(f"• {d}")


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"{cfg.agency_name} — AI Automation Dashboard | "
    f"Last refresh: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
)
