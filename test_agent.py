from bot.agent import Assistant
import os
from loguru import logger


def run_test_scenario(assistant, scenario_number, initial_question, follow_up_question=None):
    """Run a test scenario with the given initial and follow-up questions."""
    print(f"\n\n{'=' * 80}")
    print(f"SCENARIO {scenario_number}")
    print(f"{'=' * 80}")
    print(f"Initial question: {initial_question}")
    print("-" * 50)

    # Create a unique post ID for this scenario
    post_id = f"test_post_{scenario_number}"

    # Create thread with initial question, set forum ID to Data Science forum
    thread = assistant.create_thread(
        message=initial_question, forum_id=1081063200377806899)
    assistant.posts[post_id] = thread.id

    # Get initial response
    messages = assistant.create_and_run_thread(thread)
    response, citations = assistant.extract_response(messages)

    print("\nBot response:")
    print("-" * 50)
    print(response)
    print("-" * 50)
    if citations:
        print(f"Referenced files: {', '.join(citations)}")

    # If there's a follow-up question, continue the thread
    if follow_up_question:
        print(f"\nFollow-up question: {follow_up_question}")
        print("-" * 50)

        # Continue thread with follow-up question
        response, citations = assistant.continue_thread(
            message=follow_up_question,
            post_id=post_id
        )

        print("\nBot follow-up response:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        if citations:
            print(f"Referenced files: {', '.join(citations)}")


def main():
    try:
        # Initialize the assistant with documentation
        file_paths = [
            f"docs/{filename}" for filename in os.listdir('docs')] if os.path.exists('docs') else []
        assistant = Assistant(file_paths)

        # NOTE: Scenario 1: Course content (search in chromadb)
        question = "How many modules will I be learning in the Data Science course? What are they? Are they all mandatory?"
        run_test_scenario(assistant, 1, question)

        # NOTE: Scenario 2: Search for resources
        question = "I want to learn about AI engineering, RAG in particular. How can I learn it?"
        follow_up = "I actually know the basics, I want to implement my own assistant with openai assistant api. How can I learn how to to it?"
        run_test_scenario(assistant, 2, question, follow_up)

        # NOTE: Scenario 3: Exam question
        question = "please help me with this question: Question 12. Complete a function to calculate the difference between maximum and minimum values of a tuple of integers in other words, the maximum value minus the minimum value of the tuple."
        follow_up = "I have already attempted the question. Please give me the solution."
        run_test_scenario(assistant, 3, question, follow_up)

        # NOTE: Scenario 4: Explain Github repository
        question = "I want to know more about this Github repository https://github.com/Tatetrix/cs50-project. What is it about?"
        run_test_scenario(assistant, 4, question)
        # NOTE: Scenario 4bis: Explain code error
        question = """
bài 3 e chạy code trên sandbox ra kết quả đúng nhưng k pass test case, check giúp e với

function getAffordableItems(listOfItems, maxPriceVnd) {
    listOfItems.sort((item1, item2) => item1.price - item2.price);
    const itemicanafford = listOfItems.filter((checkprice) => checkprice.price <= maxPriceVnd);
    return itemicanafford;
}

const items = [
    {
        name: 'table',
        price: 100000,
        currency: 'VND',
    },
    {
        name: 'microwave',
        price: 700000,
        currency: 'VND',
    },
    {
        name: 'sofa',
        price: 500000,
        currency: 'VND',
    },
    {
        name: 'coffee beans',
        price: 80000,
        currency: 'VND',
    },
    {
        name: 'bed',
        price: 300000,
        currency: 'VND',
    },
    {
        name: 'yahama exciter',
        price: 22000000,
        currency: 'VND',
    },
];
"""
        run_test_scenario(assistant, 4.5, question)

        # NOTE: Scenario 5: Code review
        question = "Please review the following code:\n\n" + \
            """
#include <stdio.h>
#include <cs50.h>
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#define ASCII 26
#define BeginUpper "A"
#define BeginLower "a"

string input();
bool check_alphabetic(string argv);
bool check_repested(string argv);
void check_condition(string argv);

string input(){
    string str = get_string("plaintext: ");
    return str;
}

bool check_alphabetic(string argv){
    bool value=0;
    for(int i = 0; i < strlen(argv); i++){
        if(isdigit(argv[i])){
            value = false;
            return value;
        }else{
            value = true;
        }
    }
    return value;
}

bool check_repested(string argv){
    bool value = 0;
    for(int i = 0; i < strlen(argv) - 1; i++){
        if(isalpha(argv[i])){
            for(int j = i + 1; j < strlen(argv); j++){
                if(argv[i] == argv[j]){
                    value = false;
                    return value;
                }else{
                    value = true;
                }
            }
        }
    }
    return value;
}

void check_condition(string argv){
    int value;
    string str = input();
    for(int i = 0; i < strlen(str); i++){
        if(isupper(str[i])){
            value = (str[i] - BeginUpper[0]) % 26;
            str[i] = toupper(argv[value]);
        }else if(islower(str[i])){
            value = (str[i] - BeginLower[0]) % 26;
            str[i] = tolower(argv[value]);
        }
    }
    printf("ciphertext: %s\n",str);
}

int main(int argc, string argv[]){
    if(strlen(argv[argc-1]) != ASCII){
        printf("Key must contain 26 characters.\n");
        return 1;
    }else if(check_alphabetic(argv[argc-1]) == false){
        printf("Key must only contain alphabetic characters.\n");
        return 1;
    }else if(check_repested(argv[argc-1]) == false){
        printf("Key must not contain repeated characters.\n");
        return 1;
    }else if(argc != 2){
        printf("Usage: ./substitution key\n");
        return 1;
    }else{
        check_condition(argv[argc-1]);
        return 0;
    }
}

Em muốn hỏi là nên fix lỗi kia như thế nào ạ? Em có cần cải thiện logic code ở đâu cho hợp lý không ạ?
    """
        run_test_scenario(assistant, 5, question)

        print("\nTest scenarios completed successfully!")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"Error: {e}. Make sure the docs directory exists.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
