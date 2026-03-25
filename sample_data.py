"""
Seeded demo inbox — covers all three risk states and common real-world scenarios.
Each email has pre-computed analysis results so the demo never depends on API uptime.
"""

SAMPLE_EMAILS = [
    # -----------------------------------------------------------------------
    # Inbox — Safe
    # -----------------------------------------------------------------------
    {
        "id": "msg-001",
        "folder": "Inbox",
        "sender": "Campus Housing",
        "sender_email": "housing@university.edu",
        "recipient": "taylor@luman-demo.com",
        "subject": "Move-in details for next Friday",
        "preview": "Parking instructions, check-in times, and what to bring on arrival day.",
        "received": "8:42 AM",
        "status": "Safe",
        "confidence_band": "high",
        "confidence_pct": 94,
        "top_reasons": [
            "The sender address matches a real university domain.",
            "The message is informational and does not pressure you to act urgently.",
            "No links asking for personal details or account credentials were found.",
        ],
        "recommended_actions": [
            "No action required — you can read and follow the instructions normally.",
            "Reply to this address if you have questions about move-in.",
            "Stay alert to follow-up messages that unexpectedly ask for payment or login.",
        ],
        "explanation": "This looks like a routine campus update. It is calm, specific, and does not push you to act on anything sensitive.",
        "body": [
            "Hi Taylor,",
            "We are excited to welcome you to campus next Friday. Check-in will begin at 9:00 AM outside Oak Hall, and the checklist below covers what to bring on move-in day.",
            "Guest parking will be available in Lot C. If you have questions before arrival, reply to this message and our student support team will be happy to help.",
            "See you soon,",
            "Campus Housing Team",
        ],
        "simulated_link": "housing.university.edu/move-in-checklist",
        "technical_signals": {
            "urgency": False,
            "credential_request": False,
            "domain_mismatch": False,
            "shortened_link": False,
        },
    },
    # -----------------------------------------------------------------------
    # Inbox — Needs Review
    # -----------------------------------------------------------------------
    {
        "id": "msg-002",
        "folder": "Inbox",
        "sender": "QuickShip Delivery",
        "sender_email": "updates@quickship-notify.co",
        "recipient": "taylor@luman-demo.com",
        "subject": "Package delayed — confirm your address",
        "preview": "Your order is waiting for address confirmation before it can be released.",
        "received": "9:18 AM",
        "status": "Needs Review",
        "confidence_band": "medium",
        "confidence_pct": 71,
        "top_reasons": [
            "The sender domain is not a known shipping company address.",
            "The message asks you to confirm personal details through a link.",
            "Delivery delay notices are a common phishing template, though some are real.",
        ],
        "recommended_actions": [
            "Do not click the link in this message.",
            "Go directly to the shipping company's official website to track your package.",
            "If you were not expecting a delivery, ignore this message.",
            "Contact the retailer directly if you think a real package may be delayed.",
        ],
        "explanation": "This message may be real, but it asks you to confirm personal details through a link. Slow down and check through the shipping company directly.",
        "body": [
            "Hello,",
            "Your package could not be delivered because the address on file appears incomplete. Please confirm your address today so the package can be released from our holding facility.",
            "Confirm your delivery address here: http://mail.dmgratis.claimff18.my.id/paypal.com",
            "You may also check your delivery status and available offers at: https://bestdeals.com.gh/blackboard",
            "If you were expecting a delivery, it would be safer to visit the shipping company's official website directly rather than using the link in this message.",
            "Thank you,",
            "QuickShip Support",
        ],
        "simulated_link": "mail.dmgratis.claimff18.my.id/paypal.com",
        "technical_signals": {
            "urgency": True,
            "credential_request": True,
            "domain_mismatch": True,
            "shortened_link": False,
        },
    },
    # -----------------------------------------------------------------------
    # Inbox — Likely Phishing
    # -----------------------------------------------------------------------
    {
        "id": "msg-003",
        "folder": "Inbox",
        "sender": "Payroll Services",
        "sender_email": "payroll-alerts@company-payroll.help",
        "recipient": "taylor@luman-demo.com",
        "subject": "Action needed: your direct deposit is on hold",
        "preview": "We detected a problem with your payroll profile — verify it today.",
        "received": "10:07 AM",
        "status": "Likely Phishing",
        "confidence_band": "high",
        "confidence_pct": 97,
        "top_reasons": [
            "The sender domain does not match any legitimate payroll company.",
            "The message creates an artificial 2-hour deadline to pressure you into acting.",
            "You are being asked to verify sensitive financial account information through a link.",
        ],
        "recommended_actions": [
            "Do not click any links in this message.",
            "Contact your HR or payroll department directly to verify your account status.",
            "Report this email to your IT or security team.",
            "If you already clicked a link, change your work account passwords immediately.",
        ],
        "explanation": "This message uses urgency and asks you to fix sensitive financial details through a suspicious link. The domain does not match a real payroll service.",
        "body": [
            "Employee notice,",
            "Your direct deposit has been placed on hold due to a profile mismatch. To avoid a delayed paycheck, review your payroll settings immediately using the secure employee portal below.",
            "Access the employee portal now: http://mail.deliverylifesupport.com/public/iqe6Vs1h0wAgx7VmAVXhqjnzH8RM6Cdf",
            "For account support and identity verification visit: http://www.xfinitycare.free.site.pro",
            "Additional account tools: http://zmazom.cc",
            "Failure to act within 2 hours may result in payment interruption.",
            "Payroll Services",
        ],
        "simulated_link": "mail.deliverylifesupport.com/public/iqe6Vs1h0wAgx7VmAVXhqjnzH8RM6Cdf",
        "technical_signals": {
            "urgency": True,
            "credential_request": True,
            "domain_mismatch": True,
            "shortened_link": False,
        },
    },
    # -----------------------------------------------------------------------
    # Inbox — Safe
    # -----------------------------------------------------------------------
    {
        "id": "msg-004",
        "folder": "Inbox",
        "sender": "City Library",
        "sender_email": "notices@citylibrary.org",
        "recipient": "taylor@luman-demo.com",
        "subject": "Your hold is ready for pickup",
        "preview": "You can collect your book any time before Tuesday evening.",
        "received": "11:32 AM",
        "status": "Safe",
        "confidence_band": "high",
        "confidence_pct": 91,
        "top_reasons": [
            "The sender matches a well-known local institution with a standard .org domain.",
            "The message is a routine service notification with no urgent demands.",
            "No requests for personal information or account credentials were found.",
        ],
        "recommended_actions": [
            "No action required — you can pick up your hold at your convenience.",
            "Bring your library card when you visit.",
        ],
        "explanation": "This looks like a normal library service notification. It does not pressure you and the content fits a typical hold reminder.",
        "body": [
            "Hi Taylor,",
            "Your hold for 'Project Hail Mary' is ready for pickup at the downtown branch. Please bring your library card when you visit.",
            "The hold will remain available until Tuesday at 6:00 PM. After that it will be returned to the shelf.",
            "Thanks,",
            "City Library",
        ],
        "simulated_link": "citylibrary.org/account/holds",
        "technical_signals": {
            "urgency": False,
            "credential_request": False,
            "domain_mismatch": False,
            "shortened_link": False,
        },
    },
    # -----------------------------------------------------------------------
    # Inbox — Needs Review
    # -----------------------------------------------------------------------
    {
        "id": "msg-005",
        "folder": "Inbox",
        "sender": "DocuSign",
        "sender_email": "noreply@docusign-mailer.net",
        "recipient": "taylor@luman-demo.com",
        "subject": "Signature requested: internship agreement",
        "preview": "A new document is waiting for your review and signature.",
        "received": "1:14 PM",
        "status": "Needs Review",
        "confidence_band": "medium",
        "confidence_pct": 66,
        "top_reasons": [
            "The sender domain is 'docusign-mailer.net' — not the official 'docusign.com'.",
            "Signing requests create pressure to open documents quickly without verifying.",
            "DocuSign impersonation is a common phishing technique, though some are real.",
        ],
        "recommended_actions": [
            "Do not open the document link until you verify the source.",
            "Log in directly at docusign.com to see if a real document is waiting.",
            "Contact the person or organization who should have sent the agreement.",
            "If you were not expecting a document, treat this as suspicious.",
        ],
        "explanation": "The sender domain does not match official DocuSign. If you were expecting paperwork, verify it directly on the official DocuSign site before opening anything.",
        "body": [
            "Please review and sign the attached internship agreement at your earliest convenience.",
            "Open and complete your document here: https://bestconsultinternational.com/assistance",
            "Document reference and terms: https://www.boutique-dofus.fr/mmorpg/actualites/recompenses/grimoire/succes",
            "If you were not expecting this request, pause before opening anything and confirm with the organization that supposedly sent it.",
            "DocuSign Notification Center",
        ],
        "simulated_link": "bestconsultinternational.com/assistance",
        "technical_signals": {
            "urgency": False,
            "credential_request": False,
            "domain_mismatch": True,
            "shortened_link": False,
        },
    },
    # -----------------------------------------------------------------------
    # Inbox — Likely Phishing (IT Security impersonation)
    # -----------------------------------------------------------------------
    {
        "id": "msg-006",
        "folder": "Inbox",
        "sender": "IT Security Team",
        "sender_email": "security-alert@corp-helpdesk.info",
        "recipient": "taylor@luman-demo.com",
        "subject": "URGENT: Suspicious login detected on your account",
        "preview": "An unrecognized device accessed your account. Reset your password now.",
        "received": "2:55 PM",
        "status": "Likely Phishing",
        "confidence_band": "high",
        "confidence_pct": 96,
        "top_reasons": [
            "The sender domain is a generic .info address unrelated to any real IT team.",
            "The message demands immediate password reset — a classic phishing pressure tactic.",
            "Fake security alerts are one of the most common phishing templates in use.",
        ],
        "recommended_actions": [
            "Do not click any reset links in this message.",
            "Go directly to your account's official website and check for real security alerts.",
            "Change your password from the official site if you are genuinely concerned.",
            "Report this email to your IT or security team as a phishing attempt.",
        ],
        "explanation": "This message combines urgency, a fake security scare, and a suspicious domain to pressure you into clicking. Real IT teams do not send password reset links unsolicited from external .info addresses.",
        "body": [
            "Security alert,",
            "We detected a sign-in attempt from an unrecognized device in a new location. To secure your account, reset your password immediately using the link below.",
            "Reset your password now: http://zoom-call29072025callerid9237xzue07930conference-secured.s3-bkk.nipa.cloud/owa.html",
            "Join our security verification session: http://freefire1117842.keyyfirezy.biz.id",
            "Confirm your identity via secure message: http://www.whatsaap.xyz",
            "If you do not reset your password within 15 minutes, your account may be temporarily suspended for your safety.",
            "IT Security Team",
        ],
        "simulated_link": "zoom-call29072025callerid9237xzue07930conference-secured.s3-bkk.nipa.cloud/owa.html",
        "technical_signals": {
            "urgency": True,
            "credential_request": True,
            "domain_mismatch": True,
            "shortened_link": False,
        },
    },
    # -----------------------------------------------------------------------
    # Archive — Safe
    # -----------------------------------------------------------------------
    {
        "id": "msg-007",
        "folder": "Archive",
        "sender": "Amazon Order Confirmation",
        "sender_email": "order-update@amazon.com",
        "recipient": "taylor@luman-demo.com",
        "subject": "Your order has shipped",
        "preview": "Your recent order is on its way and expected to arrive Thursday.",
        "received": "Yesterday",
        "status": "Safe",
        "confidence_band": "high",
        "confidence_pct": 93,
        "top_reasons": [
            "The sender domain is the official amazon.com address.",
            "The message is a routine shipping notification with no urgent action required.",
            "No requests for personal information, passwords, or payment were found.",
        ],
        "recommended_actions": [
            "No action required — your order is on its way.",
            "Track your shipment by logging into your Amazon account directly.",
        ],
        "explanation": "This is a routine shipping confirmation from a verified Amazon address. No warning signs were detected.",
        "body": [
            "Hi Taylor,",
            "Your order is on the way. Estimated delivery is Thursday between 8 AM and 8 PM.",
            "You can track your shipment by visiting Your Orders in your Amazon account.",
            "Thanks for shopping with us,",
            "Amazon",
        ],
        "simulated_link": "amazon.com/orders/tracking",
        "technical_signals": {
            "urgency": False,
            "credential_request": False,
            "domain_mismatch": False,
            "shortened_link": False,
        },
    },
    # -----------------------------------------------------------------------
    # Archive — welcome note
    # -----------------------------------------------------------------------
    {
        "id": "msg-008",
        "folder": "Archive",
        "sender": "Luman",
        "sender_email": "hello@luman.app",
        "recipient": "taylor@luman-demo.com",
        "subject": "Welcome to your Luman inbox",
        "preview": "A quick note about how this demo experience is set up.",
        "received": "2 days ago",
        "status": "Safe",
        "confidence_band": "high",
        "confidence_pct": 99,
        "top_reasons": [
            "This is a system welcome message from within the demo itself.",
            "No external links or requests for personal information are present.",
            "The sender address matches the Luman app domain.",
        ],
        "recommended_actions": [
            "No action required — this is a welcome note.",
            "Explore the inbox to see how different risk labels look in context.",
            "Use the Scan panel to check your own messages or links.",
        ],
        "explanation": "This is a saved welcome message for the demo experience. No risk signals present.",
        "body": [
            "Welcome to Luman.",
            "This inbox uses sample emails so the review experience can be explored without connecting to a live account.",
            "Luman helps you understand whether a message is safe, worth a closer look, or a likely phishing attempt — in plain language, without security expertise.",
            "Select any message to read it, then check the Review panel on the right to see the AI analysis.",
        ],
        "simulated_link": "luman.app/demo-guide",
        "technical_signals": {
            "urgency": False,
            "credential_request": False,
            "domain_mismatch": False,
            "shortened_link": False,
        },
    },
]
