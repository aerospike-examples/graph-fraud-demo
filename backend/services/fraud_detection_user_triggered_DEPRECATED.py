from typing import List, Dict, Any
from datetime import datetime, timedelta
from models.schemas import FraudPattern, FraudResult, FraudRiskLevel

class FraudDetectionService:
    def __init__(self, graph_service):
        self.graph_service = graph_service
        self.patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> Dict[str, FraudPattern]:
        """Initialize predefined fraud detection patterns"""
        return {
            "circular_flow": FraudPattern(
                id="circular_flow",
                name="Circular Transaction Flow",
                description="Detect circular money flows between accounts via transactions",
                query="""
                g.V().hasLabel('account')
                .as('start')
                .out('TRANSFERS_TO').hasLabel('transaction')
                .out('TRANSFERS_FROM').hasLabel('account')
                .out('TRANSFERS_TO').hasLabel('transaction')
                .out('TRANSFERS_FROM').hasLabel('account')
                .out('TRANSFERS_TO').hasLabel('transaction')
                .out('TRANSFERS_FROM').hasLabel('account')
                .where(eq('start'))
                .path()
                .by(valueMap())
                """,
                risk_level=FraudRiskLevel.HIGH
            ),
            "shared_device": FraudPattern(
                id="shared_device",
                name="Shared Device Transactions",
                description="Detect transactions from the same device by different users",
                query="""
                g.V().hasLabel('transaction')
                .has('device_id')
                .group().by('device_id')
                .unfold()
                .filter(select(values).count(local).is(P.gte(2)))
                .select(values)
                .unfold()
                .valueMap()
                """,
                risk_level=FraudRiskLevel.MEDIUM
            ),
            "transaction_burst": FraudPattern(
                id="transaction_burst",
                name="Transaction Burst",
                description="Detect rapid successive transactions from same account",
                query="""
                g.V().hasLabel('account')
                .out('TRANSFERS_TO')
                .hasLabel('transaction')
                .order().by('timestamp')
                .group().by(in_('TRANSFERS_TO').values('account_id'))
                .unfold()
                .filter(select(values).count(local).is(P.gte(5)))
                .select(values)
                .unfold()
                .valueMap()
                """,
                risk_level=FraudRiskLevel.MEDIUM
            ),
            "high_amount": FraudPattern(
                id="high_amount",
                name="High Amount Transactions",
                description="Detect unusually high transaction amounts",
                query="""
                g.V().hasLabel('transaction')
                .has('amount', P.gte(5000))
                .valueMap()
                """,
                risk_level=FraudRiskLevel.HIGH
            ),
            "cross_location": FraudPattern(
                id="cross_location",
                name="Cross-Location Transactions",
                description="Detect transactions between accounts in different locations",
                query="""
                g.V().hasLabel('transaction')
                .as('tx')
                .in_('TRANSFERS_TO').hasLabel('account')
                .in_('OWNS').hasLabel('user').as('sender')
                .select('tx')
                .out('TRANSFERS_FROM').hasLabel('account')
                .in_('OWNS').hasLabel('user').as('receiver')
                .select('sender', 'receiver')
                .by('location')
                .filter(select('sender').is(P.neq(select('receiver'))))
                .select('tx')
                .valueMap()
                """,
                risk_level=FraudRiskLevel.MEDIUM
            ),
            "new_user_high_activity": FraudPattern(
                id="new_user_high_activity",
                name="New User High Activity",
                description="Detect new users with high transaction activity",
                query="""
                g.V().hasLabel('user')
                .has('signup_date', P.gte(datetime.now() - timedelta(days=7)))
                .out('OWNS').hasLabel('account')
                .out('TRANSFERS_TO')
                .hasLabel('transaction')
                .group().by(in_('TRANSFERS_TO').values('account_id'))
                .unfold()
                .filter(select(values).count(local).is(P.gte(10)))
                .select(values)
                .unfold()
                .valueMap()
                """,
                risk_level=FraudRiskLevel.HIGH
            )
        }

    async def detect_all_patterns(self) -> List[FraudResult]:
        """Run all fraud detection patterns"""
        results = []
        
        for pattern_id, pattern in self.patterns.items():
            try:
                pattern_result = await self._run_pattern(pattern)
                if pattern_result:
                    results.append(pattern_result)
            except Exception as e:
                print(f"Error running pattern {pattern_id}: {e}")
                continue
                
        return results

    async def run_specific_patterns(self, pattern_ids: List[str]) -> List[FraudResult]:
        """Run specific fraud detection patterns"""
        results = []
        
        for pattern_id in pattern_ids:
            if pattern_id in self.patterns:
                try:
                    pattern = self.patterns[pattern_id]
                    pattern_result = await self._run_pattern(pattern)
                    if pattern_result:
                        results.append(pattern_result)
                except Exception as e:
                    print(f"Error running pattern {pattern_id}: {e}")
                    continue
            else:
                print(f"Pattern {pattern_id} not found")
                
        return results

    async def _run_pattern(self, pattern: FraudPattern) -> FraudResult:
        """Execute a specific fraud detection pattern"""
        try:
            # Execute the Gremlin query
            detected_entities = await self.graph_service._execute_query(pattern.query)
            
            # Calculate risk score based on number of detected entities
            risk_score = min(len(detected_entities) * 10, 100)
            
            # Prepare details
            details = {
                "pattern_description": pattern.description,
                "entities_count": len(detected_entities),
                "risk_level": pattern.risk_level.value
            }
            
            return FraudResult(
                pattern_id=pattern.id,
                pattern_name=pattern.name,
                detected_entities=detected_entities,
                risk_score=risk_score,
                timestamp=datetime.now(),
                details=details
            )
            
        except Exception as e:
            print(f"Error executing pattern {pattern.id}: {e}")
            return None

    async def detect_circular_flows(self) -> List[Dict[str, Any]]:
        """Detect circular money flows between accounts via transactions"""
        query = """
        g.V().hasLabel('account')
        .as('start')
        .out('TRANSFERS_TO').hasLabel('transaction')
        .out('TRANSFERS_FROM').hasLabel('account')
        .out('TRANSFERS_TO').hasLabel('transaction')
        .out('TRANSFERS_FROM').hasLabel('account')
        .out('TRANSFERS_TO').hasLabel('transaction')
        .out('TRANSFERS_FROM').hasLabel('account')
        .where(eq('start'))
        .path()
        .by(valueMap())
        """
        
        try:
            results = await self.graph_service._execute_query(query)
            return results
        except Exception as e:
            print(f"Error detecting circular flows: {e}")
            return []

    async def detect_shared_devices(self) -> List[Dict[str, Any]]:
        """Detect transactions from shared devices"""
        query = """
        g.V().hasLabel('transaction')
        .has('device_id')
        .group().by('device_id')
        .unfold()
        .filter(select(values).count(local).is(P.gte(2)))
        .select(values)
        .unfold()
        .valueMap()
        """
        
        try:
            results = await self.graph_service._execute_query(query)
            return results
        except Exception as e:
            print(f"Error detecting shared devices: {e}")
            return []

    async def detect_transaction_bursts(self) -> List[Dict[str, Any]]:
        """Detect rapid successive transactions from same account"""
        query = """
        g.V().hasLabel('account')
        .out('TRANSFERS_TO')
        .hasLabel('transaction')
        .order().by('timestamp')
        .group().by(in_('TRANSFERS_TO').values('account_id'))
        .unfold()
        .filter(select(values).count(local).is(P.gte(5)))
        .select(values)
        .unfold()
        .valueMap()
        """
        
        try:
            results = await self.graph_service._execute_query(query)
            return results
        except Exception as e:
            print(f"Error detecting transaction bursts: {e}")
            return []

    async def get_available_patterns(self) -> List[FraudPattern]:
        """Get list of available fraud detection patterns"""
        return list(self.patterns.values())

    def calculate_fraud_score(self, transaction_data: Dict[str, Any]) -> float:
        """Calculate fraud score for a transaction based on various factors"""
        score = 0.0
        
        # Amount-based scoring
        amount = transaction_data.get('amount', 0)
        if amount > 10000:
            score += 30
        elif amount > 5000:
            score += 20
        elif amount > 1000:
            score += 10
            
        # Time-based scoring (transactions at unusual hours)
        timestamp = transaction_data.get('timestamp')
        if timestamp:
            hour = datetime.fromisoformat(timestamp).hour
            if hour < 6 or hour > 22:
                score += 15
                
        # Location-based scoring
        sender_location = transaction_data.get('sender_location')
        receiver_location = transaction_data.get('receiver_location')
        if sender_location and receiver_location and sender_location != receiver_location:
            score += 10
            
        # Device-based scoring
        device_id = transaction_data.get('device_id')
        if device_id:
            # This would need additional query to check device sharing
            score += 5
            
        return min(score, 100.0) 