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

# Automotive Test Engineer Prompt Template
AUTOMOTIVE_PROMPT_TEMPLATE = """You are a senior automotive test engineer working on ECU validation for production software. You are given a simplified OEM requirement document (or an expert-cleaned version), and your task is to generate technically accurate, hardware-implementable test cases suitable for integration and validation teams.

Write testcases in generic and reusable format that can be used across different ECU platforms. Each test case must be clear, concise, and executable by hardware teams using tools like Vector Canoe, CAPL, or diagnostic tools.

For each requirement in the input list, generate exactly one test case. Process each requirement independently.

Your output must be in JSON format with the following structure for each test case:
{{
  "testCaseId": "TC_001",
  "requirementId": "REQ_001", 
  "description": "[Copy requirement text exactly without changing or rephrasing]",
  "preconditions": "[ECU initialization and setup conditions]",
  "steps": ["Step 1: [Action with specific technical details]", "Step 2: [Action with specific technical details]", "Step 3: [Action with specific technical details]"],
  "expectedResult": "[Expected outcomes with specific technical responses and numbered steps]",
  "postconditions": "[System state after test execution]"
}}

### Instructions for Generating Test Cases:
- Use **numbered steps** (Step 1, Step 2, Step 3...) in the **steps** and **expectedResult** fields to clearly define actions and outcomes.
- Every step must be **factual**, **observable**, and **hardware-executable** with **specific technical implementation details**.
- Focus on **practical implementation** rather than theoretical explanations.
- Use **realistic technical language** that mirrors how human automotive testers write.
- **Minimize theory and maximize practical, executable actions**.

### Critical Requirements for Technical Specificity:

**For UDS/Diagnostic Services:**
- Always specify exact request formats and expected response formats
- Use placeholder format when exact values are not provided in requirements

**Example Input/Output Format for DIDs:**
- Test Input: `22 [DID][DID]` 
- Expected Result: `62 [DID][DID] [Data]`

**Example Input/Output Format for Security Access:**
- Test Input: `27 [SEC_LVL]`
- Expected Result: `67 [SEC_LVL] [SEED_BYTES...]`

**Example Input/Output Format for IO Control:**
- Test Input: `2F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE]`
- Expected Result: `6F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE]`

### Placeholder Handling and Technical Format:

When requirements mention UDS services, DIDs, RIDs, or IO values but do not specify exact values, use this technical format:

**For Read Data By Identifier:**
```
Step 1: Send 22 [DID][DID] request to ECU
Expected Result: ECU returns 62 [DID][DID] [Data] positive response
Where: [DID][DID] - Data Identifier from ODX/CDD, [Data] - Current I/O status
```

**For Security Access:**
```
Step 1: Send 27 [SEC_LVL] request to ECU  
Expected Result: ECU returns 67 [SEC_LVL] [SEED_BYTES...] 
Where: [SEC_LVL] - Security level, [SEED_BYTES...] - Random seed for key calculation
```

**For IO Control:**
```
Step 1: Send 2F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE] request
Expected Result: ECU returns 6F [IOI_HIGH] [IOI_LOW] [SUB_FUNCTION] [CONTROL_VALUE] positive response
Where: [IOI_HIGH][IOI_LOW] - IO Control Parameter, [SUB_FUNCTION] - Control type, [CONTROL_VALUE] - Target value
```

### Practical Implementation Focus:

- **NO lengthy theoretical explanations** about protocols or standards
- **Focus on executable actions** that can be directly implemented in test tools
- **Specify exact frame formats** for CAN/UDS communications where applicable
- **Include practical timing constraints** only when specified in requirements
- **Use concrete technical language** that hardware teams can directly execute

### Error Handling Format:

When security conditions are not met:
- Expected Result: `7F [SERVICE_ID] [NRC_CODE]` 
- Example: `7F 2F 33` (NRC_SECURITY_ACCESS_DENIED)

When invalid parameters are used:
- Expected Result: `7F [SERVICE_ID] [NRC_CODE]`
- Example: `7F 22 31` (NRC_REQUEST_OUT_OF_RANGE)

### Output Language and Format Rules:

- **Minimize explanatory text** - focus on actionable steps
- **Use technical shorthand** familiar to automotive testers
- **Avoid robotic or generic phrasing** - use practical engineering language
- **Ensure output is immediately executable** using Vector Canoe, CAPL, or diagnostic tools
- **Do not include engineering theory** unless absolutely required for test execution

### Additional Technical Guidance:

- Only include **technical calculations** if the requirement explicitly requires them for test execution
- If the requirement does NOT specify exact technical details, clearly mark as:
  - **"[Technical Detail: To be defined from ODX/CDD]"**
  - **"[Parameter: Refer to ECU specification]"**

### Final Notes:

- Return test cases in JSON array format
- Do not include extra comments or explanations outside the JSON structure
- Focus on **practical test execution** rather than comprehensive documentation
- Ensure **immediate implementability** by hardware validation teams

Testing approach: **{testability_type}** testing characteristics:
- Blackbox: Focus on input-output behavior without internal structure knowledge
- Graybox: Combine black box testing with some internal structure knowledge  
- Whitebox: Focus on internal code structure, paths, and logic

Requirements to process:
{requirements}

Generate practical automotive test cases following the above guidelines and return as JSON array."""


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
        # Parse requirements JSON
        req_data = json.loads(requirements)

        # Format the automotive prompt with the requirements and testability type
        formatted_prompt = AUTOMOTIVE_PROMPT_TEMPLATE.format(
            testability_type=testability_type,
            requirements=json.dumps(req_data, indent=2)
        )

        # Prepare initial content
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=formatted_prompt)]
            )
        ]

        # Handle optional PDF file
        if file and file.content_type == "application/pdf":
            raw = await file.read()
            contents.append(types.Content(role="user", parts=[
                types.Part(text="Attached PDF file for additional context and reference."),
                types.Part(inline_data={"mime_type": "application/pdf", "data": raw})
            ]))

        config = types.GenerateContentConfig(
            temperature=0.1,  # Very low for deterministic, consistent outputs
            top_p=0.1,        # Low for focused, deterministic responses
            max_output_tokens=8192,
        )
        
        print("Using Gemini 2.5 Flash with automotive prompt...")
        print(f"Processing {len(req_data)} requirements...")
        print("Model being used: gemini-2.0-flash-001")  # Debug line

        def sync_generate():
            response = ""
            for chunk in client.models.generate_content_stream(
                model="gemini-2.0-flash-001",  # Updated to Gemini 2.5 Pro
                contents=contents,
                config=config
            ):
                if chunk.text:
                    response += chunk.text
            return response

        response_text = await asyncio.to_thread(sync_generate)

        # Extract JSON from Gemini response
        try:
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            json_str = response_text[start_idx:end_idx] if start_idx != -1 else response_text
            test_cases_data = json.loads(json_str)

            # Convert to TestCase objects
            test_cases = []
            for i, tc_data in enumerate(test_cases_data):
                # Handle expectedResult - ensure it's a string
                expected_result = tc_data.get("expectedResult", "")
                if isinstance(expected_result, list):
                    expected_result = "\n".join(str(item) for item in expected_result)

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

            logger.info(f"Successfully generated {len(test_cases)} test cases using Gemini 2.5 Flash")
            return GenerateTestCasesResponse(testCases=test_cases, success=True)

        except json.JSONDecodeError as json_error:
            logger.error(f"Failed to parse JSON from Gemini response: {json_error}")
            logger.error(f"Raw response: {response_text[:500]}...")
            return GenerateTestCasesResponse(
                testCases=[],
                success=False,
                error="Failed to parse test cases from AI response. Please try again."
            )

    except Exception as e:
        logger.error(f"Error generating test cases: {str(e)}")
        return GenerateTestCasesResponse(
            testCases=[],
            success=False,
            error=str(e)
        )

@app.post("/api/modify-testcases", response_model=ModifyTestCasesResponse)
async def modify_test_cases(
    testCases: str = Form(...),
    modificationInstruction: str = Form(...),
    isSplitRequest: str = Form("false"),
    attachments: List[UploadFile] = File(default=[])
):
    try:
        # Parse the form data
        test_cases_data = json.loads(testCases)
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
            print(test_cases_text, modificationInstruction)

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
            print(prompt)
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
                        print(f"Trying modify model: {model_name}")
                        response = ""
                        for chunk in client.models.generate_content_stream(
                            model=model_name,
                            contents=contents,
                            config=config
                        ):
                            if chunk.text:
                                response += chunk.text
                        print(f"Success with modify model: {model_name}")
                        return response
                    except Exception as e:
                        print(f"Failed with modify {model_name}: {str(e)}")
                        continue
                
                raise Exception("All modify model variants failed")

            response_text = await asyncio.to_thread(sync_generate)

            # Extract JSON from Gemini response
            try:
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                json_str = response_text[start_idx:end_idx] if start_idx != -1 else response_text
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

            except json.JSONDecodeError:
                logger.error("Failed to parse JSON from Gemini response for modification")
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
        print("CLI Debug Mode with Gemini 2.5 Flash")
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
            print("Gemini 2.5 Flash:", cli_call())
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)