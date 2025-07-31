from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import logging, os, json, asyncio, tempfile, io, time
from google import genai
from google.genai import types
import pandas as pd
from pdf_extractor import extract_active_requirements_table
from xl_extractor import extract_full_cleaned_excel_table

# Logging config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Test Case Generator Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vertex AI Genie init
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "watchful-bonus-459710-k9")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

client = genai.Client(vertexai=True)

class Requirement(BaseModel):
    id: str
    description: str
    category: Optional[str] = None

class ExtractResponse(BaseModel):
    requirements: List[Requirement]
    success: bool
    error: Optional[str] = None

class TestCase(BaseModel):
    id: str
    testCaseId: str
    description: str
    preconditions: str
    steps: List[str]
    expectedResult: str
    testabilityType: str
    postconditions: str
    requirementId: str

class GenerateTestCasesResponse(BaseModel):
    testCases: List[TestCase]
    success: bool
    error: Optional[str] = None

class ModifyTestCasesRequest(BaseModel):
    testCases: List[TestCase]
    modificationInstruction: str
    isSplitRequest: Optional[bool] = False

class ModifyTestCasesResponse(BaseModel):
    modifiedTestCases: List[TestCase]
    success: bool
    error: Optional[str] = None

class DownloadSelectedRequest(BaseModel):
    testCases: List[TestCase]

# Fixed Automotive Test Engineer Prompt Template - keeping your exact JSON structure
def create_automotive_prompt(requirements_data, testability_type):
    """Create the automotive prompt with your exact JSON template"""
    
    # Your exact JSON template with proper parameter substitution
    template_json = {
        "Role": "TestEngineer",
        "Rule": "ECU_Validation",
        "examples": [
            "UDS Diagnostic: 22 [DID][DID] → 62 [DID][DID] [Data]",
            "Security Access: 27 [SEC_LVL] → 67 [SEC_LVL] [SEED_BYTES]",
            "IO Control: 2F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE] → 6F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE]"
        ],
        "Module": [
            {
                "play": [
                    "22 [DID][DID]",
                    "27 [SEC_LVL]",
                    "2F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE]"
                ],
                "IO": {
                    "PositiveResponse": {
                        "ReadDataById": "62 [DID][DID] [Data]",
                        "SecurityAccess": "67 [SEC_LVL] [SEED_BYTES]",
                        "IOControl": "6F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE]"
                    },
                    "NegativeResponse": {
                        "SecurityAccessDenied": "7F 2F 33",
                        "InvalidParameter": "7F 22 31"
                    }
                }
            }
        ],
        "TestCaseFormat": {
            "testCaseId": "TC_001",
            "requirementId": "REQ_001",
            "description": "[Copy requirement text exactly without changing or rephrasing]",
            "preconditions": "[ECU initialization and setup conditions]",
            "steps": [
                "Step 1: [Action with specific technical details]",
                "Step 2: [Action with specific technical details]",
                "Step 3: [Action with specific technical details]"
            ],
            "expectedResult": "[Expected outcomes with specific technical responses and numbered steps]",
            "postconditions": "[System state after test execution]"
        },
        "Instructions": {
            "StepFormat": "Numbered steps (Step 1, Step 2...)",
            "StepRequirements": [
                "Factual",
                "Observable",
                "Hardware-executable",
                "Use realistic technical language",
                "Minimize theory, maximize executable actions"
            ],
            "PracticalFocus": True
        },
        "TechnicalSpecificity": {
            "UDS": {
                "RequestFormat": "22 [DID][DID]",
                "ResponseFormat": "62 [DID][DID] [Data]"
            },
            "SecurityAccess": {
                "RequestFormat": "27 [SEC_LVL]",
                "ResponseFormat": "67 [SEC_LVL] [SEED_BYTES...]"
            },
            "IOControl": {
                "RequestFormat": "2F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE]",
                "ResponseFormat": "6F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE]"
            }
        },
        "Placeholders": {
            "ReadDID": {
                "Step": "Send 22 [DID][DID] request to ECU",
                "Expected": "ECU returns 62 [DID][DID] [Data] positive response",
                "Where": {
                    "[DID][DID]": "Data Identifier from ODX/CDD",
                    "[Data]": "Current I/O status"
                }
            },
            "SecurityAccess": {
                "Step": "Send 27 [SEC_LVL] request to ECU",
                "Expected": "ECU returns 67 [SEC_LVL] [SEED_BYTES...]",
                "Where": {
                    "[SEC_LVL]": "Security level",
                    "[SEED_BYTES...]": "Random seed for key calculation"
                }
            },
            "IOControl": {
                "Step": "Send 2F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE] request",
                "Expected": "ECU returns 6F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE] positive response",
                "Where": {
                    "[IOI_HIGH][IOI_LOW]": "IO Control Parameter",
                    "[SUB_FUNCTION]": "Control type",
                    "[CONTROL_VALUE]": "Target value"
                }
            }
        },
        "ErrorHandling": {
            "SecurityDenied": {
                "ExpectedResult": "7F 2F 33",
                "Meaning": "NRC_SECURITY_ACCESS_DENIED"
            },
            "InvalidParameter": {
                "ExpectedResult": "7F 22 31",
                "Meaning": "NRC_REQUEST_OUT_OF_RANGE"
            },
            "GeneralFormat": "7F [SERVICE_ID] [NRC_CODE]"
        },
        "OutputRules": {
            "LanguageStyle": "Technical, concise, executable",
            "Avoid": [
                "Explanatory text",
                "Robotic or generic phrasing",
                "Engineering theory unless required"
            ],
            "MustSupport": ["Vector Canoe", "CAPL", "Diagnostic Tools"]
        },
        "TechnicalGuidance": {
            "OnlyIncludeCalculationsIfRequired": True,
            "UnspecifiedParams": [
                "[Technical Detail: To be defined from ODX/CDD]",
                "[Parameter: Refer to ECU specification]"
            ]
        },
        "ExecutionNotes": {
            "ReturnFormat": "JSON array",
            "NoExtraComments": True,
            "Emphasis": "Immediate implementability"
        },
        "TestingApproach": {
            "Blackbox": "Input-output based without internal knowledge",
            "Graybox": "Partial internal structure knowledge",
            "Whitebox": "Tests internal logic/paths"
        },
        "Inputs": {
            "testability_type": testability_type,
            "requirements": requirements_data
        }
    }
    
    # Create the complete prompt with the JSON structure
    prompt = f"""You are a senior automotive test engineer working on ECU validation for production software. You are given a simplified OEM requirement document (or an expert-cleaned version), and your task is to generate technically accurate, hardware-implementable test cases suitable for integration and validation teams.

Here is your complete configuration and instructions in JSON format:

{json.dumps(template_json, indent=2)}

Based on the above configuration, generate test cases for the provided requirements. Return only a JSON array of test cases following the exact TestCaseFormat specified above."""
    
    return prompt


@app.post("/api/extract", response_model=ExtractResponse)
async def extract_requirements(
    file: UploadFile = File(...)
):
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            file_extension = file.filename.lower().split('.')[-1]
            requirements = []

            if file_extension == 'pdf':
                # Use PDF extractor
                df = extract_active_requirements_table(temp_file_path)
                if df is not None and not df.empty:
                    for index, row in df.iterrows():
                        requirements.append(Requirement(
                            id=str(row.get('Unique ID', f'REQ_{index:03d}')),
                            description=str(row.get('Name', 'No description available')),
                            category="Active Requirement"
                        ))
                else:
                    logger.warning("No requirements extracted from PDF")
                    
            elif file_extension in ['xlsx', 'xls']:
                # Use Excel extractor
                df = extract_full_cleaned_excel_table(temp_file_path)
                if df is not None and not df.empty:
                    # Assume first column is ID and second is description
                    for index, row in df.iterrows():
                        col_names = df.columns.tolist()
                        req_id = str(row.iloc[0]) if len(row) > 0 else f'REQ_{index:03d}'
                        description = str(row.iloc[1]) if len(row) > 1 else 'No description available'
                        category = str(row.iloc[2]) if len(row) > 2 else "General"
                        
                        requirements.append(Requirement(
                            id=req_id,
                            description=description,
                            category=category
                        ))
                else:
                    logger.warning("No requirements extracted from Excel")
            else:
                return ExtractResponse(
                    requirements=[],
                    success=False,
                    error=f"Unsupported file type: {file_extension}"
                )

            return ExtractResponse(
                requirements=requirements,
                success=True
            )

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except Exception as e:
        logger.error(f"Error extracting requirements: {str(e)}")
        return ExtractResponse(
            requirements=[],
            success=False,
            error=str(e)
        )

@app.post("/api/generate-testcases", response_model=GenerateTestCasesResponse)
async def generate_test_cases(
    requirements: str = Form(...),
    testability_type: str = Form(...),
    file: UploadFile = File(None)  # Make file optional
):
    try:
        # Parse requirements JSON with better error handling
        try:
            req_data = json.loads(requirements)
            logger.info(f"Successfully parsed {len(req_data)} requirements")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse requirements JSON: {str(e)}")
            logger.error(f"Requirements string: {requirements[:500]}...")
            return GenerateTestCasesResponse(
                testCases=[],
                success=False,
                error=f"Invalid JSON in requirements: {str(e)}"
            )

        # Create the automotive prompt using the new function with your exact JSON structure
        formatted_prompt = create_automotive_prompt(req_data, testability_type)

        # Prepare initial content
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=formatted_prompt)]
            )
        ]

        # Handle optional PDF file
        if file and file.content_type == "application/pdf":
            try:
                raw = await file.read()
                contents.append(types.Content(role="user", parts=[
                    types.Part(text="Attached PDF file for additional context and reference."),
                    types.Part(inline_data={"mime_type": "application/pdf", "data": raw})
                ]))
                logger.info("PDF file attached to request")
            except Exception as e:
                logger.warning(f"Failed to process PDF attachment: {str(e)}")

        config = types.GenerateContentConfig(
            temperature=0.1,  # Very low for deterministic, consistent outputs
            top_p=0.1,        # Low for focused, deterministic responses
            max_output_tokens=8192,
        )
        
        logger.info("Using Gemini 2.0 Flash with automotive prompt...")
        logger.info(f"Processing {len(req_data)} requirements...")
        logger.info("Model being used: gemini-2.0-flash-001")

        def sync_generate():
            response = ""
            try:
                for chunk in client.models.generate_content_stream(
                    model="gemini-2.0-flash-001",
                    contents=contents,
                    config=config
                ):
                    if chunk.text:
                        response += chunk.text
                return response
            except Exception as e:
                logger.error(f"Error in sync_generate: {str(e)}")
                raise

        response_text = await asyncio.to_thread(sync_generate)
        logger.info(f"Received response from Gemini: {len(response_text)} characters")

        # Extract JSON from Gemini response with better error handling
        try:
            # Try to find JSON array in response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.error("No JSON array found in response")
                logger.error(f"Response preview: {response_text[:1000]}...")
                return GenerateTestCasesResponse(
                    testCases=[],
                    success=False,
                    error="No valid JSON array found in AI response. Please try again."
                )
            
            json_str = response_text[start_idx:end_idx]
            logger.info(f"Extracted JSON string: {len(json_str)} characters")
            
            test_cases_data = json.loads(json_str)
            logger.info(f"Successfully parsed {len(test_cases_data)} test cases from JSON")

            # Convert to TestCase objects
            test_cases = []
            for i, tc_data in enumerate(test_cases_data):
                try:
                    # Handle expectedResult - ensure it's a string
                    expected_result = tc_data.get("expectedResult", "")
                    if isinstance(expected_result, list):
                        expected_result = " ".join(str(item) for item in expected_result)

                    test_cases.append(TestCase(
                        id=f"tc-{i+1}",
                        testCaseId=tc_data.get("testCaseId", f"TC_{i+1:03d}"),
                        requirementId=tc_data.get("requirementId") or tc_data.get("RequirmentId", ""),
                        description=tc_data.get("description", ""),
                        preconditions=tc_data.get("preconditions", ""),
                        steps=tc_data.get("steps", []),
                        expectedResult=expected_result,
                        testabilityType=testability_type,
                        postconditions=tc_data.get("postconditions", "")
                    ))
                except Exception as e:
                    logger.error(f"Error processing test case {i}: {str(e)}")
                    continue

            logger.info(f"Successfully generated {len(test_cases)} test cases using Gemini 2.0 Flash")
            return GenerateTestCasesResponse(testCases=test_cases, success=True)

        except json.JSONDecodeError as json_error:
            logger.error(f"Failed to parse JSON from Gemini response: {json_error}")
            logger.error(f"JSON string that failed: {json_str[:500] if 'json_str' in locals() else 'N/A'}...")
            logger.error(f"Raw response preview: {response_text[:1000]}...")
            return GenerateTestCasesResponse(
                testCases=[],
                success=False,
                error="Failed to parse test cases from AI response. The AI response was not in valid JSON format. Please try again."
            )

    except Exception as e:
        logger.error(f"Error generating test cases: {str(e)}", exc_info=True)
        return GenerateTestCasesResponse(
            testCases=[],
            success=False,
            error=f"Unexpected error: {str(e)}"
        )

@app.post("/api/modify-testcases", response_model=ModifyTestCasesResponse)
async def modify_test_cases(
    testCases: str = Form(...),
    modificationInstruction: str = Form(...),
    isSplitRequest: str = Form("false"),
    attachments: List[UploadFile] = File(default=[])
):
    try:
        # Parse the form data with better error handling
        try:
            test_cases_data = json.loads(testCases)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse test cases JSON: {str(e)}")
            return ModifyTestCasesResponse(
                modifiedTestCases=[],
                success=False,
                error=f"Invalid JSON in test cases: {str(e)}"
            )
            
        is_split_request = isSplitRequest.lower() == "true"
        
        # Convert to TestCase objects
        test_cases = []
        for tc_data in test_cases_data:
            # Ensure expectedResult is a string
            expected_result = tc_data.get("expectedResult", "")
            if isinstance(expected_result, list):
                expected_result = "\n".join(str(item) for item in expected_result)
            
            test_cases.append(TestCase(
                id=tc_data["id"],
                testCaseId=tc_data["testCaseId"],
                requirementId=tc_data["requirementId"],
                description=tc_data["description"],
                preconditions=tc_data["preconditions"],
                steps=tc_data["steps"],
                expectedResult=expected_result,
                testabilityType=tc_data["testabilityType"],
                postconditions=tc_data["postconditions"]
            ))

        # Group test cases by requirement ID to get context
        test_cases_by_req = {}
        for tc in test_cases:
            req_id = tc.requirementId
            if req_id not in test_cases_by_req:
                test_cases_by_req[req_id] = []
            test_cases_by_req[req_id].append(tc)

        modified_test_cases = []
        
        for req_id, test_cases_list in test_cases_by_req.items():
            # Prepare the modification prompt
            test_cases_text = ""
            for tc in test_cases_list:
                test_cases_text += f"""
                Test Case ID: {tc.testCaseId}
                Description: {tc.description}
                Preconditions: {tc.preconditions}
                Steps: {'; '.join(tc.steps)}
                Expected Result: {tc.expectedResult}
                Postconditions: {tc.postconditions}
                ---
                """
            logger.info(f"Processing {len(test_cases_list)} test cases for requirement {req_id}")

            # Customize prompt based on whether it's a split request
            if is_split_request:
                prompt = f"""
You are a senior automotive test engineer. Below are test cases that need to be split according to the user's instruction.

Original Test Cases:
{test_cases_text}

User wants to split the test cases with this instruction:
"{modificationInstruction}"

Please split each test case into multiple new test cases as requested. For each original test case, create multiple new test cases that cover different aspects or scenarios of the original test case.

Return the new test cases in JSON format as an array. Each split test case should have:
- A unique testCaseId (e.g., TC_001_A, TC_001_B for splits of TC_001)
- The same requirementId as the original
- Focused description for the specific scenario
- Appropriate preconditions, steps, and expected results
- Same postconditions or modified as needed

Format:
[
  {{
    "testCaseId": "TC_001_A",
    "requirementId": "{req_id}",
    "description": "Specific scenario A description",
    "preconditions": "Preconditions for scenario A",
    "steps": ["Step 1", "Step 2"],
    "expectedResult": "Expected result for scenario A",
    "postconditions": "Postconditions for scenario A"
  }},
  {{
    "testCaseId": "TC_001_B", 
    "requirementId": "{req_id}",
    "description": "Specific scenario B description",
    "preconditions": "Preconditions for scenario B",
    "steps": ["Step 1", "Step 2"],
    "expectedResult": "Expected result for scenario B",
    "postconditions": "Postconditions for scenario B"
  }}
]

Make sure each split test case is focused and comprehensive with automotive engineering precision.
                """
            else:
                prompt = f"""
You are a senior automotive test engineer. Below are test cases that need to be modified according to the user's instruction.

Original Test Cases:
{test_cases_text}

User wants to modify the test cases with this instruction:
"{modificationInstruction}"

Please return the updated versions of these test cases in the same JSON format, keeping the same structure but applying the requested modifications. Apply automotive engineering best practices and maintain technical accuracy.

Return as a JSON array with this exact structure:
[
  {{
    "testCaseId": "TC_001",
    "requirementId": "{req_id}",
    "description": "Updated description",
    "preconditions": "Updated preconditions",
    "steps": ["Step 1", "Step 2"],
    "expectedResult": "Updated expected result",
    "postconditions": "Updated postconditions"
  }}
]

Make sure to preserve the original test case IDs and requirement IDs while applying the modifications with automotive engineering precision.
                """
            
            # Prepare content for Gemini
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part(text=prompt)]
                )
            ]

            # Process attachments and add them to the content
            for attachment in attachments:
                try:
                    file_content = await attachment.read()
                    
                    # Add file content to Gemini request based on file type
                    if attachment.content_type == "application/pdf":
                        contents.append(types.Content(
                            role="user",
                            parts=[
                                types.Part(text=f"Reference document: {attachment.filename}"),
                                types.Part(inline_data={"mime_type": "application/pdf", "data": file_content})
                            ]
                        ))
                    elif attachment.content_type == "text/plain":
                        text_content = file_content.decode('utf-8')
                        contents.append(types.Content(
                            role="user",
                            parts=[types.Part(text=f"Reference text file '{attachment.filename}':\n{text_content}")]
                        ))
                    elif attachment.content_type.startswith("image/"):
                        contents.append(types.Content(
                            role="user",
                            parts=[
                                types.Part(text=f"Reference image: {attachment.filename}"),
                                types.Part(inline_data={"mime_type": attachment.content_type, "data": file_content})
                            ]
                        ))
                    elif attachment.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        contents.append(types.Content(
                            role="user",
                            parts=[types.Part(text=f"Reference document: {attachment.filename} (DOCX file attached)")]
                        ))
                        
                except Exception as e:
                    logger.warning(f"Failed to process attachment {attachment.filename}: {str(e)}")
                    continue

            config = types.GenerateContentConfig(
                temperature=0.7,  # Very low for deterministic outputs
                top_p=0.9,        # Low for focused, consistent responses
                max_output_tokens=8192,
            )

            def sync_generate():
                # Try multiple model names in case one doesn't work
                model_names = [
                    "gemini-2.0-flash-001",
                    "gemini-2.0-flash-001", 
                    "gemini-2.0-flash-001",
                    "gemini-2.0-flash"
                ]
                
                for model_name in model_names:
                    try:
                        logger.info(f"Trying modify model: {model_name}")
                        response = ""
                        for chunk in client.models.generate_content_stream(
                            model=model_name,
                            contents=contents,
                            config=config
                        ):
                            if chunk.text:
                                response += chunk.text
                        logger.info(f"Success with modify model: {model_name}")
                        return response
                    except Exception as e:
                        logger.error(f"Failed with modify {model_name}: {str(e)}")
                        continue
                
                raise Exception("All modify model variants failed")

            response_text = await asyncio.to_thread(sync_generate)

            # Extract JSON from Gemini response with better error handling
            try:
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                
                if start_idx == -1 or end_idx == 0:
                    logger.error("No JSON array found in modify response")
                    # Return original test cases if parsing fails
                    modified_test_cases.extend(test_cases_list)
                    continue
                    
                json_str = response_text[start_idx:end_idx]
                modified_data = json.loads(json_str)

                # Convert to TestCase objects
                for i, tc_data in enumerate(modified_data):
                    # Ensure expectedResult is a string
                    expected_result = tc_data.get("expectedResult", "")
                    if isinstance(expected_result, list):
                        expected_result = "\n".join(str(item) for item in expected_result)

                    if is_split_request:
                        # For split requests, create new test cases
                        modified_test_cases.append(TestCase(
                            id=f"tc-split-{len(modified_test_cases)+1}-{int(time.time())}",
                            testCaseId=tc_data.get("testCaseId", f"TC_{len(modified_test_cases)+1:03d}"),
                            requirementId=tc_data.get("requirementId", req_id),
                            description=tc_data.get("description", ""),
                            preconditions=tc_data.get("preconditions", ""),
                            steps=tc_data.get("steps", []),
                            expectedResult=expected_result,
                            testabilityType=test_cases_list[0].testabilityType if test_cases_list else "blackbox",
                            postconditions=tc_data.get("postconditions", "")
                        ))
                    else:
                        # For regular modifications, preserve original IDs
                        original_tc = test_cases_list[i] if i < len(test_cases_list) else test_cases_list[0]
                        modified_test_cases.append(TestCase(
                            id=original_tc.id,
                            testCaseId=tc_data.get("testCaseId", original_tc.testCaseId),
                            requirementId=tc_data.get("requirementId", original_tc.requirementId),
                            description=tc_data.get("description", original_tc.description),
                            preconditions=tc_data.get("preconditions", original_tc.preconditions),
                            steps=tc_data.get("steps", original_tc.steps),
                            expectedResult=expected_result,
                            testabilityType=original_tc.testabilityType,
                            postconditions=tc_data.get("postconditions", original_tc.postconditions)
                        ))

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Gemini response for modification: {str(e)}")
                # Return original test cases if parsing fails
                modified_test_cases.extend(test_cases_list)

        return ModifyTestCasesResponse(modifiedTestCases=modified_test_cases, success=True)

    except Exception as e:
        logger.error(f"Error modifying test cases: {str(e)}")
        return ModifyTestCasesResponse(
            modifiedTestCases=[],
            success=False,
            error=str(e)
        )

@app.post("/api/download-selected")
async def download_selected_test_cases(request: DownloadSelectedRequest):
    try:
        # Generate CSV content
        headers = [
            "Test Case ID",
            "Requirement ID", 
            "Description",
            "Preconditions",
            "Steps",
            "Expected Result",
            "Postconditions",
            "Testability Type",
        ]
        
        csv_rows = [headers]
        
        for testCase in request.testCases:
            row = [
                testCase.testCaseId,
                testCase.requirementId,
                testCase.description,
                testCase.preconditions,
                "; ".join(testCase.steps),
                testCase.expectedResult,
                testCase.postconditions,
                testCase.testabilityType,
            ]
            csv_rows.append(row)
        
        # Create CSV content
        csv_content = ""
        for row in csv_rows:
            # Escape quotes and wrap in quotes if needed
            escaped_row = []
            for cell in row:
                cell_str = str(cell)
                if '"' in cell_str:
                    cell_str = cell_str.replace('"', '""')
                if ',' in cell_str or '"' in cell_str or '\n' in cell_str:
                    cell_str = f'"{cell_str}"'
                escaped_row.append(cell_str)
            csv_content += ",".join(escaped_row) + "\n"
        
        # Create a BytesIO object to stream the CSV
        csv_buffer = io.BytesIO(csv_content.encode('utf-8'))
        
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=selected-test-cases.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error downloading selected test cases: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "model": "gemini-2.0-flash-001"}

if __name__ == "__main__":
    import uvicorn
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    if DEBUG_MODE:
        print("CLI Debug Mode with Gemini 2.0 Flash")
        while True:
            u = input("You: ")
            if u.lower() in ("exit", "quit"):
                break
            def cli_call():
                return client.models.generate_content(
                    model="gemini-2.0-flash-001",  # Official stable model name
                    contents=[types.Part(text=u)],
                    config=types.GenerateContentConfig(
                        temperature=0.1,  # Deterministic for CLI too
                        top_p=0.1,
                        max_output_tokens=1024,
                    )
                ).text
            print("Gemini 2.0 Flash:", cli_call())
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)