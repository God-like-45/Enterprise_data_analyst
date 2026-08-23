import time
from app.agent.sql_agent import sql_agent
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# A benchmark suite of enterprise evaluation questions
EVAL_DATASET = [
    {
        "question": "What are the top 5 most expensive products?",
        "expected_keyword": "ORDER BY price DESC"
    },
    {
        "question": "Show me the total revenue grouped by product category name.",
        "expected_keyword": "GROUP BY"
    },
    {
        "question": "Which customer made the largest single order by total amount?",
        "expected_keyword": "MAX(total_amount)"
    }
]

def test_agent_evaluation_benchmark():
    """Runs the agent through a standard enterprise benchmark suite and tracks success rate."""
    successful_runs = 0
    total_tests = len(EVAL_DATASET)
    
    print("\n================ EVALUATION BENCHMARK START ================")
    
    for idx, test_case in enumerate(EVAL_DATASET):
        question = test_case["question"]
        expected = test_case["expected_keyword"]
        
        logger.info(f"Evaluating Benchmark [{idx+1}/{total_tests}]: {question}")
        
        start_time = time.time()
        result = sql_agent.answer_question(question)
        duration = time.time() - start_time
        
        # FIX: Correctly check the nested database_result success flag
        db_res = result.get("database_result", {})
        is_success = db_res.get("success", False)
        generated_sql = result.get("generated_sql", "")
        
        print(f"\n[Test {idx+1}] Question: {question}")
        print(f"Status: {'PASSED ✅' if is_success else 'FAILED ❌'}")
        print(f"Latency: {duration:.2f} seconds")
        print(f"Generated SQL:\n{generated_sql}")
        if not is_success:
            print(f"Error:\n{result.get('error', 'No error reported')}")
        
        if is_success:
            successful_runs += 1
            
    accuracy_score = (successful_runs / total_tests) * 100
    print(f"\n================ BENCHMARK RESULTS ================")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {successful_runs}")
    print(f"Accuracy Rate: {accuracy_score:.1f}%")
    print(f"===================================================\n")
    
    assert accuracy_score >= 66.0, "Benchmark accuracy dropped below the 66% enterprise threshold!"