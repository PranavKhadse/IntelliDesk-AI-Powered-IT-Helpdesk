import os
import sys
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.ticket import Category, Ticket, TicketStatus, TicketPriority
from app.models.comment import TicketComment, CommentType
from app.models.kb_article import KBArticle
from app.models.audit_log import AuditLog, AuditAction


def seed_database():
    print("[+] Initializing database seeding...")
    db = SessionLocal()

    try:
        # 1. Clear existing records for clean idempotent seeding
        db.query(AuditLog).delete()
        db.query(TicketComment).delete()
        db.query(Ticket).delete()
        db.query(KBArticle).delete()
        db.query(Category).delete()
        db.query(User).delete()
        db.commit()

        # 2. Seed Categories
        categories_data = [
            {"name": "Hardware", "description": "Laptops, monitors, docks, keyboards, printers", "default_sla_hours": 12},
            {"name": "Software", "description": "Application installs, OS updates, licensing errors", "default_sla_hours": 24},
            {"name": "Network & Connectivity", "description": "Office Wi-Fi, VPN access, Ethernet, firewall blocks", "default_sla_hours": 8},
            {"name": "Access & Permissions", "description": "Active Directory, SSO, GitHub/AWS role grants", "default_sla_hours": 4},
            {"name": "Email & Collaboration", "description": "Outlook, Teams, Slack, Google Workspace sync", "default_sla_hours": 12},
            {"name": "Cloud & Infrastructure", "description": "Server outages, database connections, CI/CD runners", "default_sla_hours": 6},
        ]
        
        categories = {}
        for cat_info in categories_data:
            cat = Category(**cat_info, is_active=True)
            db.add(cat)
            db.flush()
            categories[cat.name] = cat

        print(f"[+] Seeded {len(categories)} IT Categories.")

        # 3. Seed Users
        users_data = [
            {
                "email": "admin@intellidesk.com",
                "password": "AdminPass123!",
                "full_name": "Alex Vance (IT Director)",
                "department": "IT Operations",
                "role": UserRole.ADMIN
            },
            {
                "email": "sarah.chen@intellidesk.com",
                "password": "AgentPass123!",
                "full_name": "Sarah Chen",
                "department": "Tier 2 Support",
                "role": UserRole.AGENT
            },
            {
                "email": "marcus.brooks@intellidesk.com",
                "password": "AgentPass123!",
                "full_name": "Marcus Brooks",
                "department": "Network Operations",
                "role": UserRole.AGENT
            },
            {
                "email": "john.doe@company.com",
                "password": "UserPass123!",
                "full_name": "John Doe",
                "department": "Finance",
                "role": UserRole.USER
            },
            {
                "email": "emily.smith@company.com",
                "password": "UserPass123!",
                "full_name": "Emily Smith",
                "department": "Engineering",
                "role": UserRole.USER
            },
        ]

        users = {}
        for u_info in users_data:
            pwd = u_info.pop("password")
            user = User(
                **u_info,
                hashed_password=get_password_hash(pwd),
                is_active=True
            )
            db.add(user)
            db.flush()
            users[user.email] = user

        print(f"[+] Seeded {len(users)} Users across Admin, Agent, and User roles.")

        # 4. Seed Sample Knowledge Base Articles
        now = datetime.now(timezone.utc)
        kb_data = [
            {
                "title": "Configuring GlobalProtect Corporate VPN",
                "slug": "configuring-globalprotect-vpn",
                "summary": "Step-by-step instructions for connecting to the company VPN using GlobalProtect and MFA.",
                "content": """# GlobalProtect VPN Configuration Guide

### Overview
This guide provides complete instructions to install and authenticate to the GlobalProtect VPN portal.

### Steps to Connect:
1. Download GlobalProtect from `https://vpn.company.internal`.
2. Enter the portal address: `portal.vpn.company.com`.
3. When prompted, enter your standard company email and password.
4. Approve the push notification on your Okta Verify / Authenticator mobile app.
5. Once connected, the status icon in your system tray will turn green.

### Troubleshooting:
- **Error: 'Connection Failed'**: Verify your home Wi-Fi is not blocking UDP port 4500.
- **Error: 'Gateway Unavailable'**: Try changing the gateway location to `US-East-Backup` in VPN settings.
""",
                "category_id": categories["Network & Connectivity"].id,
                "author_id": users["sarah.chen@intellidesk.com"].id,
                "tags": "vpn,network,remote,globalprotect",
                "view_count": 142,
                "helpful_count": 28
            },
            {
                "title": "Troubleshooting USB-C Docking Stations & Multi-Monitors",
                "slug": "troubleshooting-usbc-docking-stations",
                "summary": "Fix display flicker, external monitor detection issues, and USB peripheral dropouts on Dell/Lenovo docks.",
                "content": """# USB-C Docking Station Troubleshooting

### Common Symptoms:
- External monitors show "No Signal" after laptop sleeps.
- Keyboard and mouse intermittently lag or disconnect.

### Quick Fixes:
1. **Power Cycle the Dock**: Unplug the power adapter from the docking station, wait 15 seconds, and plug back in.
2. **DisplayPort Topology**: Open Intel Graphics Command Center and ensure DisplayPort 1.4 is selected.
3. **Thunderbolt Firmware Update**: Open Dell Command Update / Lenovo Vantage and apply all pending firmware updates.
""",
                "category_id": categories["Hardware"].id,
                "author_id": users["marcus.brooks@intellidesk.com"].id,
                "tags": "hardware,dock,monitor,display,usbc",
                "view_count": 89,
                "helpful_count": 19
            },
            {
                "title": "Requesting Production AWS & Kubernetes Cluster Access",
                "slug": "requesting-aws-k8s-access",
                "summary": "Standard Operating Procedure for requesting temporary elevated IAM roles and kubectl tokens.",
                "content": """# Production Access Request SOP

### Policy Requirements:
All access to production AWS accounts and EKS clusters requires an approved Jira change ticket and manager sign-off.

### Request Flow:
1. Submit an Access & Permissions ticket referencing your Jira deployment ID.
2. Specify the exact role needed (e.g., `ReadOnly-ClusterViewer` vs `Emergency-Admin`).
3. Approvals are auto-provisioned for a maximum 8-hour TTL.
""",
                "category_id": categories["Access & Permissions"].id,
                "author_id": users["admin@intellidesk.com"].id,
                "tags": "access,aws,kubernetes,iam,security",
                "view_count": 210,
                "helpful_count": 45
            }
        ]

        for kb_info in kb_data:
            kb = KBArticle(**kb_info, is_published=True)
            db.add(kb)

        print(f"[+] Seeded {len(kb_data)} Knowledge Base Articles.")

        # 5. Seed Sample Tickets with Comments & Audit Trails
        tickets_data = [
            {
                "ticket_number": "IT-1001",
                "title": "Cannot connect to Office Wi-Fi from MacBook Pro",
                "description": "Since morning, my MacBook repeatedly disconnects from 'Corp-Secure-5G' and asks for certificate re-verification. Need this fixed before client presentation.",
                "status": TicketStatus.IN_PROGRESS,
                "priority": TicketPriority.HIGH,
                "category_id": categories["Network & Connectivity"].id,
                "creator_id": users["john.doe@company.com"].id,
                "assignee_id": users["marcus.brooks@intellidesk.com"].id,
                "sla_due_at": now + timedelta(hours=4),
                "comments": [
                    {
                        "author_id": users["marcus.brooks@intellidesk.com"].id,
                        "comment_type": CommentType.PUBLIC,
                        "content": "Hi John, looking into the Wi-Fi RADIUS logs now. Can you check if removing the old 802.1X certificate from Keychain solves the loop?"
                    },
                    {
                        "author_id": users["marcus.brooks@intellidesk.com"].id,
                        "comment_type": CommentType.INTERNAL_NOTE,
                        "content": "RADIUS server cert expired at 00:00 UTC. Deployed renewal profile to MDM group 4."
                    }
                ]
            },
            {
                "ticket_number": "IT-1002",
                "title": "Need JetBrains All-Products license assigned to GitHub profile",
                "description": "Starting on the backend microservices refactor this sprint. Requesting IDE license allocation for IntelliJ Ultimate & PyCharm.",
                "status": TicketStatus.OPEN,
                "priority": TicketPriority.MEDIUM,
                "category_id": categories["Software"].id,
                "creator_id": users["emily.smith@company.com"].id,
                "assignee_id": users["sarah.chen@intellidesk.com"].id,
                "sla_due_at": now + timedelta(hours=20),
                "comments": []
            },
            {
                "ticket_number": "IT-1003",
                "title": "External monitor flickering via Dell WD19 docking station",
                "description": "Main 4K monitor goes black for 2 seconds every few minutes when connected through the dock.",
                "status": TicketStatus.RESOLVED,
                "priority": TicketPriority.LOW,
                "category_id": categories["Hardware"].id,
                "creator_id": users["john.doe@company.com"].id,
                "assignee_id": users["sarah.chen@intellidesk.com"].id,
                "sla_due_at": now - timedelta(hours=10),
                "resolved_at": now - timedelta(hours=2),
                "comments": [
                    {
                        "author_id": users["sarah.chen@intellidesk.com"].id,
                        "comment_type": CommentType.PUBLIC,
                        "content": "Updated the Thunderbolt 3 controller firmware to v1.0.8 and replaced the high-speed DP cable. Monitor is stable now."
                    }
                ]
            },
            {
                "ticket_number": "IT-1004",
                "title": "URGENT: Locked out of AWS Production Console",
                "description": "MFA device battery died and cannot generate OTP for root incident triage on prod DB cluster.",
                "status": TicketStatus.OPEN,
                "priority": TicketPriority.CRITICAL,
                "category_id": categories["Access & Permissions"].id,
                "creator_id": users["emily.smith@company.com"].id,
                "assignee_id": users["admin@intellidesk.com"].id,
                "sla_due_at": now + timedelta(hours=1),
                "comments": [
                    {
                        "author_id": users["admin@intellidesk.com"].id,
                        "comment_type": CommentType.PUBLIC,
                        "content": "Initiating identity verification protocol via phone before issuing temporary hardware token."
                    }
                ]
            }
        ]

        for t_info in tickets_data:
            comments_info = t_info.pop("comments", [])
            ticket = Ticket(**t_info)
            db.add(ticket)
            db.flush()

            # Add creation audit log
            audit = AuditLog(
                ticket_id=ticket.id,
                actor_id=ticket.creator_id,
                action=AuditAction.CREATED,
                new_state=f'{{"status": "{ticket.status}", "priority": "{ticket.priority}"}}'
            )
            db.add(audit)

            # Add comments
            for c_info in comments_info:
                comment = TicketComment(ticket_id=ticket.id, **c_info)
                db.add(comment)

        db.commit()
        print(f"[+] Seeded {len(tickets_data)} Sample Tickets with threaded comments and audit trails.")
        print("[SUCCESS] Database seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding failed: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
