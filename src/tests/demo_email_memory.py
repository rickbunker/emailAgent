"""
Email Memory System Demo

This script demonstrates how the memory system would work for email management
by populating it with realistic data and running sample queries.
"""

import asyncio
import time
from typing import List
from ..memory.procedural import ProceduralMemory
from ..memory.semantic import SemanticMemory
from ..memory.episodic import EpisodicMemory

class EmailMemoryDemo:
    def __init__(self):
        self.procedural = ProceduralMemory(max_items=1000)
        self.semantic = SemanticMemory(max_items=1000)
        self.episodic = EpisodicMemory(max_items=1000)

    async def setup_demo_data(self):
        """Populate the memory system with realistic email management data."""
        print("🧠 Setting up demo data for email memory system...")
        
        # Clear existing data
        await self.procedural.clear_collection(force_delete=True)
        await self.semantic.clear_collection(force_delete=True)
        await self.episodic.clear_collection(force_delete=True)
        
        await self._populate_procedural_memory()
        await self._populate_semantic_memory()
        await self._populate_episodic_memory()
        
        print("✅ Demo data setup complete!\n")

    async def _populate_procedural_memory(self):
        """Add email handling rules and procedures."""
        print("📋 Adding procedural memory (rules and procedures)...")
        
        rules = [
            # Spam and Security Rules
            {
                "content": "Immediately flag emails with suspicious attachments (.exe, .scr, .bat files) as potential malware",
                "metadata": {"category": "security", "priority": "critical", "action": "flag"}
            },
            {
                "content": "Mark emails with multiple spelling errors and urgent money requests as likely spam",
                "metadata": {"category": "spam", "priority": "high", "action": "spam_filter"}
            },
            {
                "content": "Auto-delete emails from known scam domains and blacklisted senders",
                "metadata": {"category": "spam", "priority": "high", "action": "delete"}
            },
            
            # Priority and Response Rules
            {
                "content": "Always prioritize emails from family members and mark as urgent",
                "metadata": {"category": "priority", "priority": "high", "sender_type": "family"}
            },
            {
                "content": "Respond to work emails within 4 hours during business hours",
                "metadata": {"category": "response_time", "priority": "medium", "timeframe": "4_hours"}
            },
            {
                "content": "Auto-respond to newsletter subscriptions with unsubscribe confirmation",
                "metadata": {"category": "automation", "priority": "low", "action": "auto_respond"}
            },
            
            # Organization Rules
            {
                "content": "Archive emails older than 6 months unless they contain important keywords",
                "metadata": {"category": "maintenance", "priority": "low", "action": "archive"}
            },
            {
                "content": "Categorize financial emails (banks, credit cards, investments) into Finance folder",
                "metadata": {"category": "organization", "priority": "medium", "folder": "Finance"}
            },
            {
                "content": "Extract contact information from legitimate business emails for contact database",
                "metadata": {"category": "contact_management", "priority": "medium", "action": "extract_contacts"}
            }
        ]
        
        for rule in rules:
            await self.procedural.add(rule["content"], rule["metadata"])
        
        print(f"   Added {len(rules)} procedural rules")

    async def _populate_semantic_memory(self):
        """Add knowledge about senders and email patterns."""
        print("🧠 Adding semantic memory (sender knowledge)...")
        
        knowledge = [
            # Trusted Senders
            {
                "content": "John Smith from Acme Corp sends weekly project updates every Monday morning, usually contains meeting schedules and deliverable status",
                "metadata": {
                    "sender": "john.smith@acmecorp.com", 
                    "sender_type": "colleague", 
                    "trust_level": "high",
                    "email_pattern": "weekly_updates",
                    "company": "Acme Corp",
                    "typical_subject": "Weekly Project Update"
                }
            },
            {
                "content": "Sarah Johnson is the HR director, sends policy updates and meeting invitations, always professional and legitimate",
                "metadata": {
                    "sender": "sarah.johnson@company.com",
                    "sender_type": "hr",
                    "trust_level": "high",
                    "role": "HR Director",
                    "email_pattern": "policy_updates"
                }
            },
            {
                "content": "Mom sends family updates and photos, often with subject lines about family events or holiday plans",
                "metadata": {
                    "sender": "mom@familyemail.com",
                    "sender_type": "family",
                    "trust_level": "highest",
                    "relationship": "mother",
                    "email_pattern": "family_updates"
                }
            },
            
            # Business Contacts
            {
                "content": "TechVendor Inc support team provides technical assistance, legitimate company with real support tickets",
                "metadata": {
                    "sender": "support@techvendor.com",
                    "sender_type": "vendor",
                    "trust_level": "medium",
                    "company": "TechVendor Inc",
                    "service_type": "technical_support"
                }
            },
            {
                "content": "City Bank sends account statements and security alerts, legitimate financial institution",
                "metadata": {
                    "sender": "alerts@citybank.com",
                    "sender_type": "financial",
                    "trust_level": "high",
                    "institution": "City Bank",
                    "email_pattern": "financial_updates"
                }
            },
            
            # Known Spam Patterns
            {
                "content": "Emails from random Gmail accounts with urgent lottery winnings or inheritance claims are always scams",
                "metadata": {
                    "sender_type": "scammer",
                    "trust_level": "none",
                    "spam_pattern": "lottery_scam",
                    "domain_pattern": "random_gmail"
                }
            },
            {
                "content": "Phishing emails impersonating major banks often have slight domain misspellings and urgent action requests",
                "metadata": {
                    "sender_type": "phisher",
                    "trust_level": "none",
                    "spam_pattern": "bank_phishing",
                    "red_flags": "domain_misspelling, urgent_action"
                }
            },
            
            # Newsletter and Automation
            {
                "content": "TechNews Daily sends daily technology newsletters, subscribed voluntarily, legitimate but low priority",
                "metadata": {
                    "sender": "newsletter@technews.com",
                    "sender_type": "newsletter",
                    "trust_level": "medium",
                    "subscription_status": "voluntary",
                    "frequency": "daily"
                }
            }
        ]
        
        for item in knowledge:
            await self.semantic.add(item["content"], item["metadata"])
        
        print(f"   Added {len(knowledge)} knowledge items")

    async def _populate_episodic_memory(self):
        """Add conversation history and learning experiences."""
        print("📝 Adding episodic memory (conversation history)...")
        
        conversations = [
            # User Feedback and Learning
            {
                "content": "User corrected: Email from recruiter@newcompany.com was legitimate job inquiry, not spam",
                "metadata": {
                    "type": "user_feedback",
                    "correction": "false_positive",
                    "sender": "recruiter@newcompany.com",
                    "timestamp": time.time() - 86400,  # 1 day ago
                    "learning": "recruitment_emails_legitimate"
                }
            },
            {
                "content": "User reported: Newsletter from dealsite@offers.com is unwanted spam despite appearing legitimate",
                "metadata": {
                    "type": "user_feedback", 
                    "correction": "false_negative",
                    "sender": "dealsite@offers.com",
                    "timestamp": time.time() - 172800,  # 2 days ago
                    "learning": "deal_newsletters_unwanted"
                }
            },
            {
                "content": "Successfully extracted contact info: Dr. Lisa Chen, Cardiology Associates, phone: 555-0123",
                "metadata": {
                    "type": "extraction_success",
                    "contact_name": "Dr. Lisa Chen",
                    "organization": "Cardiology Associates", 
                    "phone": "555-0123",
                    "timestamp": time.time() - 259200  # 3 days ago
                }
            },
            
            # Agent Actions and Results
            {
                "content": "Auto-responded to conference invitation with calendar availability request",
                "metadata": {
                    "type": "agent_action",
                    "action": "auto_respond",
                    "sender": "events@techconference.com",
                    "result": "successful",
                    "timestamp": time.time() - 3600  # 1 hour ago
                }
            },
            {
                "content": "Quarantined suspicious email claiming to be from bank with misspelled domain",
                "metadata": {
                    "type": "security_action", 
                    "action": "quarantine",
                    "reason": "domain_suspicious",
                    "sender": "alerts@ctiybank.com",  # Note the misspelling
                    "timestamp": time.time() - 7200  # 2 hours ago
                }
            },
            
            # Pattern Recognition
            {
                "content": "Identified pattern: Emails from *.contractor.com domain are legitimate work-related communications",
                "metadata": {
                    "type": "pattern_learning",
                    "pattern": "contractor_domain_legitimate",
                    "domain_pattern": "*.contractor.com",
                    "confidence": "high",
                    "timestamp": time.time() - 432000  # 5 days ago
                }
            }
        ]
        
        for conversation in conversations:
            await self.episodic.add(conversation["content"], conversation["metadata"])
        
        print(f"   Added {len(conversations)} conversation records")

    async def run_demo_queries(self):
        """Run sample queries to demonstrate the system."""
        print("🔍 Running demo queries to show email management capabilities...\n")
        
        await self._demo_spam_detection()
        await self._demo_priority_management()
        await self._demo_contact_extraction()
        await self._demo_learning_from_feedback()
        await self._demo_sender_analysis()

    async def _demo_spam_detection(self):
        """Demonstrate spam detection capabilities."""
        print("🚫 SPAM DETECTION DEMO")
        print("=" * 50)
        
        # Query for spam detection rules
        spam_rules = await self.procedural.search("spam suspicious malware", limit=3)
        print("📋 Relevant spam detection rules:")
        for rule in spam_rules:
            print(f"   • {rule.content}")
            print(f"     Category: {rule.metadata.get('category', 'N/A')}, Priority: {rule.metadata.get('priority', 'N/A')}")
        
        # Query for known spam patterns
        spam_patterns = await self.semantic.search("scam phishing lottery", limit=3)
        print("\n🧠 Known spam patterns:")
        for pattern in spam_patterns:
            print(f"   • {pattern.content}")
            print(f"     Trust Level: {pattern.metadata.get('trust_level', 'N/A')}")
        
        # Check past security actions
        security_actions = await self.episodic.search("quarantine suspicious domain")
        print(f"\n📝 Recent security actions taken: {len(security_actions)} incidents")
        for action in security_actions[:2]:
            print(f"   • {action.content}")
        
        print("\n")

    async def _demo_priority_management(self):
        """Demonstrate email priority management."""
        print("⭐ PRIORITY MANAGEMENT DEMO")
        print("=" * 50)
        
        # Query for priority rules
        priority_rules = await self.procedural.search("priority urgent family work", limit=3)
        print("📋 Priority management rules:")
        for rule in priority_rules:
            print(f"   • {rule.content}")
            print(f"     Priority: {rule.metadata.get('priority', 'N/A')}")
        
        # Query for high-trust senders
        trusted_senders = await self.semantic.search("family colleague trust", 
                                                    filter={
                                                        "must": [
                                                            {"key": "metadata.trust_level", "match": {"value": "high"}}
                                                        ]
                                                    })
        print(f"\n🧠 High-trust senders identified: {len(trusted_senders)}")
        for sender in trusted_senders:
            print(f"   • {sender.metadata.get('sender', 'Unknown')}: {sender.content[:80]}...")
        
        print("\n")

    async def _demo_contact_extraction(self):
        """Demonstrate contact extraction capabilities."""
        print("👥 CONTACT EXTRACTION DEMO")
        print("=" * 50)
        
        # Query for contact extraction rules
        contact_rules = await self.procedural.search("contact information extract", limit=2)
        print("📋 Contact extraction rules:")
        for rule in contact_rules:
            print(f"   • {rule.content}")
        
        # Query for successful extractions
        extractions = await self.episodic.search("extracted contact", 
                                                filter={
                                                    "must": [
                                                        {"key": "metadata.type", "match": {"value": "extraction_success"}}
                                                    ]
                                                })
        print(f"\n📝 Successful contact extractions: {len(extractions)}")
        for extraction in extractions:
            metadata = extraction.metadata
            print(f"   • {metadata.get('contact_name', 'N/A')} from {metadata.get('organization', 'N/A')}")
            if metadata.get('phone'):
                print(f"     Phone: {metadata.get('phone')}")
        
        print("\n")

    async def _demo_learning_from_feedback(self):
        """Demonstrate learning from user feedback."""
        print("🎓 LEARNING FROM FEEDBACK DEMO")
        print("=" * 50)
        
        # Query for user corrections
        feedback = await self.episodic.search("user corrected reported feedback",
                                             filter={
                                                 "must": [
                                                     {"key": "metadata.type", "match": {"value": "user_feedback"}}
                                                 ]
                                             })
        print(f"📝 User feedback records: {len(feedback)}")
        for fb in feedback:
            correction_type = fb.metadata.get('correction', 'unknown')
            sender = fb.metadata.get('sender', 'unknown')
            print(f"   • {correction_type.upper()}: {fb.content}")
            print(f"     Sender: {sender}")
            print(f"     Learning: {fb.metadata.get('learning', 'N/A')}")
        
        print("\n")

    async def _demo_sender_analysis(self):
        """Demonstrate comprehensive sender analysis."""
        print("🔍 SENDER ANALYSIS DEMO")
        print("=" * 50)
        
        print("Analyzing sender: john.smith@acmecorp.com")
        
        # Get sender knowledge
        sender_info = await self.semantic.search("john.smith@acmecorp.com OR Acme Corp")
        if sender_info:
            info = sender_info[0]
            print(f"📊 Sender Profile:")
            print(f"   • Trust Level: {info.metadata.get('trust_level', 'Unknown')}")
            print(f"   • Sender Type: {info.metadata.get('sender_type', 'Unknown')}")
            print(f"   • Company: {info.metadata.get('company', 'Unknown')}")
            print(f"   • Pattern: {info.metadata.get('email_pattern', 'Unknown')}")
            print(f"   • Description: {info.content}")
        
        # Check for applicable rules
        applicable_rules = await self.procedural.search("work colleague priority")
        print(f"\n📋 Applicable rules: {len(applicable_rules)}")
        for rule in applicable_rules[:2]:
            print(f"   • {rule.content}")
        
        print("\n")

async def main():
    """Run the complete email memory demo."""
    demo = EmailMemoryDemo()
    
    print("🚀 EMAIL MEMORY SYSTEM DEMO")
    print("Creating sample data and running queries...")
    
    try:
        await demo.setup_demo_data()
        await demo.run_demo_queries()
        
        print("🎉 DEMO COMPLETE!")
        print("=" * 60)
        print("The memory system is ready to help manage your email!")
        print("\nWhat this demo shows:")
        print("📋 Procedural Memory: Rules for handling different email types")
        print("🧠 Semantic Memory: Knowledge about senders and patterns") 
        print("📝 Episodic Memory: Learning from past decisions and actions")
        print("\nNext steps for your email agent:")
        print("• Connect to Gmail API to get real emails")
        print("• Build agent layer to apply these memories")
        print("• Add real-time learning from your decisions")
        print("• Implement automated actions based on rules")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 