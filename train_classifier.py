"""
Offline training script for Luman's lightweight email classifier.
Run once to produce model.joblib and vectorizer.joblib.

Usage:
    python train_classifier.py
    python train_classifier.py --spam-csv /path/to/spam.csv   # optional Kaggle dataset
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------------------------
# Label constants
# ---------------------------------------------------------------------------
LABELS = ["Safe", "Needs Review", "Likely Phishing"]
LABEL_TO_INT = {l: i for i, l in enumerate(LABELS)}

# ---------------------------------------------------------------------------
# Built-in training corpus
# ---------------------------------------------------------------------------
# Each entry: (text, label)
# Designed to cover realistic email patterns across all three risk states.

CORPUS: list[tuple[str, str]] = [
    # ── Likely Phishing ──────────────────────────────────────────────────────
    (
        "Your account has been suspended. Verify your identity immediately to restore access. "
        "Click the link below or your account will be permanently deleted within 24 hours.",
        "Likely Phishing",
    ),
    (
        "URGENT: We detected suspicious activity on your bank account. "
        "Your account is now locked. Please verify your details at the secure link below to unlock it.",
        "Likely Phishing",
    ),
    (
        "Congratulations! You have been selected as a winner of our $1,000,000 lottery prize. "
        "To claim your winnings, send your full name, address, and bank account number.",
        "Likely Phishing",
    ),
    (
        "ACTION REQUIRED: Your direct deposit is on hold. A mismatch was found in your payroll profile. "
        "Verify your account within 2 hours or your paycheck will be delayed.",
        "Likely Phishing",
    ),
    (
        "Your Apple ID has been locked due to too many failed sign-in attempts. "
        "Click here to verify your information and unlock your account immediately.",
        "Likely Phishing",
    ),
    (
        "IRS Tax Refund Notice: You are eligible for a $2,847 refund. "
        "Submit your personal and banking details now to receive your refund within 48 hours.",
        "Likely Phishing",
    ),
    (
        "SECURITY ALERT: An unrecognized device just signed into your account from a new location. "
        "Reset your password immediately using the link below or your account will be suspended.",
        "Likely Phishing",
    ),
    (
        "Your Microsoft 365 password expires today. Click here to keep your account active. "
        "Failure to update will result in loss of access to all Microsoft services.",
        "Likely Phishing",
    ),
    (
        "We noticed your PayPal account may have been accessed without authorization. "
        "Your account has been limited. Confirm your identity now to restore full access.",
        "Likely Phishing",
    ),
    (
        "FINAL NOTICE: Your Netflix subscription has failed to renew due to a payment issue. "
        "Update your billing information now to avoid service interruption.",
        "Likely Phishing",
    ),
    (
        "Amazon: Your account will be closed. We noticed unusual activity. "
        "Verify your account information to keep your Prime membership active.",
        "Likely Phishing",
    ),
    (
        "HR Department: Your employee benefits enrollment is expiring. "
        "Log in immediately to confirm your selections or you will lose your coverage.",
        "Likely Phishing",
    ),
    (
        "Your package could not be delivered. Pay a small redelivery fee of $1.99 to release your parcel. "
        "Click the link below to complete payment. This offer expires in 12 hours.",
        "Likely Phishing",
    ),
    (
        "ALERT: Your Social Security number has been suspended due to suspicious activity. "
        "Call our toll-free number immediately to reactivate your SSN and avoid legal action.",
        "Likely Phishing",
    ),
    (
        "DocuSign: You have received a document requiring your signature. "
        "Your identity must be verified before you can access the document. Enter your credentials.",
        "Likely Phishing",
    ),
    (
        "Your Chase bank statement is ready. We detected unusual login activity. "
        "Confirm your account credentials now to prevent unauthorized transactions.",
        "Likely Phishing",
    ),
    (
        "Zoom: Your account has been flagged for review. "
        "To avoid termination, verify your account by clicking the secure link and entering your login details.",
        "Likely Phishing",
    ),
    (
        "You have a pending wire transfer of $45,000. "
        "Confirm your bank details to complete the transaction. This offer expires in 24 hours.",
        "Likely Phishing",
    ),
    (
        "IT Support: Your email account will be deactivated due to inactivity. "
        "Re-authenticate using your username and password to keep your account active.",
        "Likely Phishing",
    ),
    (
        "ACCOUNT VERIFICATION REQUIRED: Your account shows signs of fraudulent activity. "
        "Immediate action is required. Click the link to verify your identity or face account closure.",
        "Likely Phishing",
    ),
    (
        "Congratulations! You have won a free iPhone 15. "
        "Complete the short survey and pay a small shipping fee to claim your prize today.",
        "Likely Phishing",
    ),
    (
        "Your direct deposit failed. Please re-enter your bank routing and account number "
        "immediately to ensure your paycheck is processed.",
        "Likely Phishing",
    ),
    (
        "Google Security Alert: Someone tried to sign in to your Google Account. "
        "If this was not you, click here to secure your account and reset your password now.",
        "Likely Phishing",
    ),
    (
        "Your Venmo account has been flagged. To avoid permanent suspension, verify your "
        "identity by providing your full name, date of birth, and social security number.",
        "Likely Phishing",
    ),
    (
        "Federal grant approval: You have been approved for a $45,000 government grant. "
        "Submit your bank account details to receive your funds within 3 business days.",
        "Likely Phishing",
    ),
    (
        "FINAL WARNING: Your account will be permanently deleted unless you verify your identity. "
        "We require your full name, email, password, and credit card number for verification.",
        "Likely Phishing",
    ),
    (
        "Your insurance claim has been approved. To receive your reimbursement of $3,200, "
        "confirm your bank account details by clicking the secure link below.",
        "Likely Phishing",
    ),
    (
        "WIN FREE CASH! You have been selected for a special promotion. "
        "Claim your $500 gift card now. Limited time offer — act before midnight tonight.",
        "Likely Phishing",
    ),
    (
        "Your credit card was charged $799 for a subscription renewal. "
        "If you did not authorize this charge, call our fraud department immediately and provide your card details.",
        "Likely Phishing",
    ),
    (
        "Password expiration notice: Your network password will expire in 1 hour. "
        "Enter your current password and new password below to avoid being locked out.",
        "Likely Phishing",
    ),

    # ── Needs Review ─────────────────────────────────────────────────────────
    (
        "Your package is on its way. We were unable to deliver your parcel today. "
        "Please click the link to reschedule delivery to your address.",
        "Needs Review",
    ),
    (
        "A document has been sent to you for review and signature. "
        "Please click the button below to view and sign the document at your earliest convenience.",
        "Needs Review",
    ),
    (
        "Your subscription is due for renewal in 3 days. "
        "To continue without interruption, please update your payment method.",
        "Needs Review",
    ),
    (
        "We noticed a sign-in to your account from a new device. "
        "If this was you, no action is needed. If not, please review your account activity.",
        "Needs Review",
    ),
    (
        "Your account verification is pending. Please complete the verification process "
        "to ensure continued access to all features.",
        "Needs Review",
    ),
    (
        "We have a job opportunity that matches your profile. "
        "Please review the attached offer letter and confirm your interest by end of day.",
        "Needs Review",
    ),
    (
        "Reminder: Your annual benefits enrollment window closes Friday. "
        "Log in to your HR portal to review and confirm your selections.",
        "Needs Review",
    ),
    (
        "Your domain registration expires in 7 days. "
        "To avoid losing your domain, please renew it using the link below.",
        "Needs Review",
    ),
    (
        "QuickShip: Your delivery could not be completed. Please confirm your address "
        "using the link provided so we can redeliver your package.",
        "Needs Review",
    ),
    (
        "You have a new voicemail message. Listen to your voicemail by clicking the link. "
        "This message will expire in 7 days.",
        "Needs Review",
    ),
    (
        "Your free trial ends soon. Upgrade to the full plan to keep your features. "
        "Click here to choose a plan that works for you.",
        "Needs Review",
    ),
    (
        "An invoice has been generated for your account. "
        "Please review and pay by the due date to avoid a late fee.",
        "Needs Review",
    ),
    (
        "You have been added as a collaborator on a shared document. "
        "Please click the link to view and accept the invitation.",
        "Needs Review",
    ),
    (
        "Your annual performance review is ready. Please log in to complete the self-assessment "
        "before the deadline at the end of the month.",
        "Needs Review",
    ),
    (
        "We are updating our terms of service. Please log in to review and accept the new terms "
        "to continue using our platform.",
        "Needs Review",
    ),
    (
        "Your account has been idle for 30 days. To keep your account active, "
        "please log in within the next 7 days.",
        "Needs Review",
    ),
    (
        "A new shared calendar invite has been sent to you. "
        "Please accept or decline the invitation by clicking the link below.",
        "Needs Review",
    ),
    (
        "We noticed unusual activity on your account. As a precaution, "
        "we have temporarily limited some features. Please review your recent activity.",
        "Needs Review",
    ),
    (
        "Please verify your email address to complete your registration. "
        "Click the link below to confirm your account.",
        "Needs Review",
    ),
    (
        "Your cloud storage is 90% full. Upgrade your plan or delete files to free up space. "
        "Click here to manage your storage.",
        "Needs Review",
    ),
    (
        "A password change was requested for your account. If you made this request, "
        "click the link to set a new password. If not, you can ignore this message.",
        "Needs Review",
    ),
    (
        "Reminder: You have an incomplete application. Return to the application portal "
        "to finish and submit your form before the deadline.",
        "Needs Review",
    ),
    (
        "Your scheduled appointment is coming up. Please confirm your attendance "
        "by clicking the link or call us to reschedule.",
        "Needs Review",
    ),
    (
        "You have been invited to join a Slack workspace. Click accept to get started "
        "and connect with your team.",
        "Needs Review",
    ),
    (
        "Action needed: Please complete your two-factor authentication setup "
        "to improve the security of your account.",
        "Needs Review",
    ),

    # ── Safe ─────────────────────────────────────────────────────────────────
    (
        "Hi Taylor, your order has been confirmed and will ship by Thursday. "
        "Thank you for shopping with us. You can track your order from your account page.",
        "Safe",
    ),
    (
        "Your hold is ready for pickup at the library. The item will be held for 7 days. "
        "Please bring your library card when you visit.",
        "Safe",
    ),
    (
        "Welcome to our platform! We are glad you are here. "
        "Get started by exploring the features in your new account.",
        "Safe",
    ),
    (
        "Your flight is confirmed. Departure: Tuesday at 7:45 AM. "
        "Your boarding pass will be available 24 hours before departure.",
        "Safe",
    ),
    (
        "This is a reminder that your appointment is scheduled for Monday at 2:00 PM. "
        "Please arrive 10 minutes early. Call us if you need to reschedule.",
        "Safe",
    ),
    (
        "Your monthly statement is available. You can view it by logging into your account. "
        "Your balance this month is $247.50.",
        "Safe",
    ),
    (
        "Thank you for your donation! Your contribution of $50 to the Food Bank "
        "will make a real difference. Your receipt is attached.",
        "Safe",
    ),
    (
        "Your package has been delivered. It was left at your front door at 2:14 PM. "
        "If you have any questions, contact the retailer directly.",
        "Safe",
    ),
    (
        "Move-in day is next Friday! Check-in begins at 9:00 AM at the main office. "
        "Remember to bring your ID and signed lease. See you soon!",
        "Safe",
    ),
    (
        "Your weekly newsletter is here. Read this week's top stories on our website. "
        "You can manage your subscription preferences at any time.",
        "Safe",
    ),
    (
        "Hi there, just a quick note — the meeting scheduled for Wednesday has been moved to Thursday "
        "at the same time. The conference room is booked. See you then.",
        "Safe",
    ),
    (
        "Your tax documents are ready to download. Log in to your account to access your "
        "W-2 and other year-end documents for the previous tax year.",
        "Safe",
    ),
    (
        "Thank you for attending our event! We hope you enjoyed the session. "
        "A recording will be available on our website within 24 hours.",
        "Safe",
    ),
    (
        "Your GitHub pull request has been reviewed. Two comments were left by your team member. "
        "Visit the pull request to view the feedback.",
        "Safe",
    ),
    (
        "Reminder: your annual physical is scheduled for next Tuesday at 10:00 AM. "
        "Please remember to fast for 8 hours beforehand and bring your insurance card.",
        "Safe",
    ),
    (
        "Your lease renewal documents are attached. Please review and sign by the end of the month "
        "if you wish to continue your tenancy.",
        "Safe",
    ),
    (
        "Good news! Your application has been approved. We will contact you within 5 business days "
        "with the next steps in the process.",
        "Safe",
    ),
    (
        "This week in technology: top stories from the past seven days. "
        "Click any headline to read the full article on our site.",
        "Safe",
    ),
    (
        "Your Amazon order has shipped. Your estimated delivery date is Thursday. "
        "You can track your shipment from your orders page.",
        "Safe",
    ),
    (
        "Campus housing: parking instructions for move-in week are now posted. "
        "Lot C will be reserved for new residents on Friday and Saturday.",
        "Safe",
    ),
    (
        "The team lunch is confirmed for Friday at noon. We will be at the Italian place around the corner. "
        "RSVP by Thursday so we can give the restaurant an accurate count.",
        "Safe",
    ),
    (
        "Your prescription is ready for pickup at the pharmacy. "
        "You can pick it up any time during regular business hours.",
        "Safe",
    ),
    (
        "Here is your receipt for the purchase you made today. Total: $23.47. "
        "Thank you for your business. Keep this email for your records.",
        "Safe",
    ),
    (
        "Congratulations on your promotion! It is well deserved. "
        "The HR team will be in touch with updated paperwork by the end of the week.",
        "Safe",
    ),
    (
        "Your gym membership renews automatically on the 1st of next month. "
        "No action is needed. You can update your preferences from the member portal.",
        "Safe",
    ),
    (
        "Your annual subscription has been renewed at the same rate as last year. "
        "Your card ending in 4242 was charged $99. Thank you for being a loyal subscriber.",
        "Safe",
    ),
    (
        "Thank you for completing our survey. Your responses have been recorded. "
        "We appreciate your feedback and will use it to improve our service.",
        "Safe",
    ),
    (
        "Your background check is complete. Results have been sent to the organization that requested it. "
        "Log in to view your full report.",
        "Safe",
    ),
    (
        "Hi, just following up on the project timeline we discussed. "
        "Let me know if you have any updates or need more time on the deliverable.",
        "Safe",
    ),
    (
        "Your boarding pass for flight AA 2281 is attached. Gate B12. Boards at 6:15 AM. "
        "Have a great trip!",
        "Safe",
    ),
]


def _load_spam_csv(path: str) -> list[tuple[str, str]]:
    """
    Load the Kaggle spam CSV (columns: v1=ham/spam, v2=text).
    Maps ham → Safe, spam → Likely Phishing.
    Caps at 2000 rows to keep training fast.
    """
    try:
        import pandas as pd
        df = pd.read_csv(path, encoding="latin-1", usecols=["v1", "v2"])
        df = df.dropna(subset=["v1", "v2"])
        label_map = {"ham": "Safe", "spam": "Likely Phishing"}
        df["label"] = df["v1"].map(label_map)
        df = df.dropna(subset=["label"])
        # Balance classes: cap ham to 3x spam count
        spam = df[df["label"] == "Likely Phishing"].head(700)
        ham  = df[df["label"] == "Safe"].head(700)
        df = pd.concat([spam, ham], ignore_index=True)
        return list(zip(df["v2"].tolist(), df["label"].tolist()))
    except Exception as exc:
        print(f"[warn] Could not load spam CSV: {exc}")
        return []


def train(spam_csv: str | None = None, out_dir: str = ".") -> None:
    texts, labels = zip(*CORPUS)
    texts = list(texts)
    labels = list(labels)

    if spam_csv:
        extra = _load_spam_csv(spam_csv)
        if extra:
            print(f"[info] Loaded {len(extra)} rows from {spam_csv}")
            for t, l in extra:
                texts.append(t)
                labels.append(l)

    y = [LABEL_TO_INT[l] for l in labels]

    vec = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=8000,
        sublinear_tf=True,
        strip_accents="unicode",
        min_df=1,
    )
    X = vec.fit_transform(texts)

    clf = LogisticRegression(
        C=1.0,
        max_iter=500,
        class_weight="balanced",
        solver="lbfgs",
    )
    clf.fit(X, y)

    # Quick eval on a held-out split (only if dataset is large enough)
    if len(texts) >= 40:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        clf_eval = LogisticRegression(
            C=1.0, max_iter=500, class_weight="balanced",
            solver="lbfgs",
        )
        clf_eval.fit(X_tr, y_tr)
        y_pred = clf_eval.predict(X_te)
        print("\n── Evaluation (20% held-out) ──────────────────────")
        print(classification_report(y_te, y_pred, target_names=LABELS))

    # Save final model trained on full data
    out = Path(out_dir)
    joblib.dump(clf, out / "model.joblib")
    joblib.dump(vec, out / "vectorizer.joblib")
    print(f"\n[ok] Saved model.joblib and vectorizer.joblib to {out.resolve()}")
    print(f"     Trained on {len(texts)} examples across {len(set(labels))} classes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Luman email classifier")
    parser.add_argument("--spam-csv", default=None, help="Path to Kaggle spam.csv")
    parser.add_argument("--out-dir", default=".", help="Output directory for model files")
    args = parser.parse_args()
    train(spam_csv=args.spam_csv, out_dir=args.out_dir)
