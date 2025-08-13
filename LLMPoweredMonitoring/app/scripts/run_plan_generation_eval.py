#!/usr/bin/env python3
"""
Simple runner script for plan generation e2e evaluation.
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.ai.test_plan_generation import test_plan_generation_e2e

def main():
    print("=" * 60)
    print("🧪 Plan Generation E2E Evaluation Runner")
    print("=" * 60)
    
    try:
        results = test_plan_generation_e2e()
        
        if results:
            print("\n" + "=" * 60)
            print("✅ Evaluation completed successfully!")
            print("📊 Check the output above for detailed results.")
        else:
            print("\n" + "=" * 60)
            print("❌ Evaluation failed or returned no results.")
            
    except Exception as e:
        print(f"\n💥 Evaluation runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
