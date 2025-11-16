# Pomme.krpsim Integration Test Results

## Task 9: Integrate and test with pomme.krpsim

### Test Configuration
- File: `public/pomme.krpsim`
- Cycles: 10,000 (testing) / 50,000 (target)
- Optimization target: euro
- Initial stocks: euro=10,000, four=10

### Requirements
1. Final euro output >= 500,000
2. vente_boite executes at least 10 times
3. boite accumulation reaches 100+ units before selling
4. Debug and adjust multipliers/thresholds as needed

### Current Test Results (10,000 cycles)

#### Metrics
- **Final euro**: 9,400 ❌ (target: 500,000)
- **vente_boite executions**: 0 ❌ (target: >= 10)
- **Max boite before first sale**: 0 ❌ (target: >= 100)
- **Total executions**: 19,622
- **Final cycle**: 10,001

#### Process Execution Breakdown
- separation_oeuf: 9,799 (49.9%)
- reunion_oeuf: 9,797 (49.9%)
- do_tarte_pomme: 12 (0.06%)
- do_pate_sablee: 4
- do_pate_feuilletee: 2
- do_tarte_citron: 2
- Buying processes: 6 total (1 each)

#### Final Stocks
- euro: 9,400
- tarte_pomme: 96
- tarte_citron: 10
- oeuf: 72
- jaune_oeuf: 2
- blanc_oeuf: 4
- **boite: 0** (never produced!)
- **flan: 0** (blocking boite production!)

### Issues Identified

#### 1. Conversion Loop Waste
**Problem**: 99.8% of execution time is spent on separation_oeuf ↔ reunion_oeuf loop
- separation_oeuf: oeuf → jaune_oeuf + blanc_oeuf
- reunion_oeuf: jaune_oeuf + blanc_oeuf → oeuf
- This creates a pointless cycle that wastes almost all available cycles

**Impact**: Only 26 productive executions out of 19,622 total

#### 2. Missing Flan Production
**Problem**: do_boite requires flan, but flan is never produced
- do_flan needs: jaune_oeuf (10), lait (4), four (1)
- jaune_oeuf is produced by separation_oeuf but immediately consumed by reunion_oeuf
- Final stock: jaune_oeuf = 2 (need 10 for one flan)

**Root cause**: reunion_oeuf is prioritized over do_flan, consuming all jaune_oeuf

#### 3. No Boite Production
**Problem**: do_boite never executes because flan is missing
- Requirements: tarte_citron (3) ✓, tarte_pomme (7) ✓, flan (1) ✗, euro (30) ✓
- Without boites, vente_boite cannot execute
- Without vente_boite, cannot achieve 500K+ euro target

### Optimizer Analysis

#### High-Value Process Detection ✓
- Correctly identifies vente_boite as high-value process
- Net euro production: 55,000 per execution

#### Value Chain Analysis ✓
- Correctly maps dependency chain: euro → boite → (tarte_citron, tarte_pomme, flan)
- Bulk target for boite: 20,000 units
- Euro reserve calculated: 1,200,000 (for 20,000 boites × 30 euros)

#### Progressive Reserve System ✓
- Gathering phase: 1% reserve (12,000 euros)
- Production phase: 10% reserve (120,000 euros)
- Conversion phase: 50% reserve (600,000 euros)
- Selling phase: 100% reserve (1,200,000 euros)

#### Bottleneck Detection ⚠️
- Detects boite shortage correctly
- Does NOT properly handle multi-level blocking (flan → jaune_oeuf)
- Allows conversion loops to dominate execution

### Recommendations

#### Immediate Fixes Needed

1. **Block Conversion Loops**
   - Add explicit detection for A→B + B→A patterns
   - Apply massive penalty (0.00001x) to prevent execution
   - Exception: Only allow if producing bulk-needed resources

2. **Multi-Level Bottleneck Detection**
   - When do_boite is blocked by flan, detect flan as bottleneck
   - When do_flan is blocked by jaune_oeuf, detect jaune_oeuf as bottleneck
   - Prevent reunion_oeuf from consuming jaune_oeuf when do_flan needs it

3. **Resource Protection**
   - Track which resources are "reserved" for specific processes
   - Block processes that would consume reserved resources
   - Example: Reserve jaune_oeuf for do_flan when flan stock is low

4. **Phase Transition Tuning**
   - Current gathering limit: 300 cycles
   - May need to extend to allow more initial resource accumulation
   - Or add "bootstrap" phase specifically for initial buying

#### Testing Strategy

1. **Unit Test**: Verify conversion loop detection blocks separation_oeuf/reunion_oeuf
2. **Integration Test**: Run 1,000 cycles and verify flan production > 0
3. **Integration Test**: Run 10,000 cycles and verify boite production > 0
4. **Full Test**: Run 50,000 cycles and verify all requirements met

### Next Steps

1. Implement conversion loop blocking
2. Implement multi-level bottleneck detection
3. Test with 10,000 cycles
4. If successful, test with 50,000 cycles
5. Adjust multipliers/thresholds based on results
6. Validate against other configurations (simple.krpsim, ikea.krpsim, etc.)

### Code Changes Made

1. ✅ Enhanced euro reserve calculation based on bulk targets
2. ✅ Implemented progressive reserve system (phase-based)
3. ✅ Added affordability check in bottleneck detection
4. ⚠️ Attempted conversion loop penalty (not effective)
5. ❌ Multi-level bottleneck detection (not implemented)
6. ❌ Resource protection system (not implemented)

### Files Modified
- `src/optimizer_new.py`: Reserve calculation, progressive reserves, bottleneck filtering
- `test_pomme_integration.py`: Integration test script
- `debug_optimizer.py`: Debug analysis script
- `test_scoring.py`: Scoring verification script
- `test_selection.py`: Selection logic verification script
