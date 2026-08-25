from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from code_agent_service import code_agent

app = FastAPI(title="代码生成Agent API")

class CodeRequest(BaseModel):
    requirement: str
    mode: str = "code"  # code 或 test

class CodeResponse(BaseModel):
    status: str
    code: str = ""
    test_code: str = ""
    result: str = ""
    attempts: int

@app.post("/code/generate", response_model=CodeResponse)
def generate(request: CodeRequest):
    try:
        result = code_agent(request.requirement, mode=request.mode)
        return CodeResponse(
            status=result.get("status", "unknown"),
            code=result.get("code", ""),
            test_code=result.get("test_code", ""),
            result=result.get("result", ""),
            attempts=result.get("attempts", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))