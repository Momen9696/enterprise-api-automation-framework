"""Authentication, authorization, payload, type, identity, and method failures."""

*** Settings ***
Documentation    Negative API scenarios. Passwords used here are deliberately wrong.
Resource         ../../resources/users.resource
Suite Setup      Framework Is Ready

*** Test Cases ***
Invalid Credentials
    ${body}=    Create Dictionary    email=customer@demo.local    password=wrong-password
    ${response}=    Post Request    /auth/login    ${body}    use_auth=${False}
    Response Status Should Be    ${response}    401
    Response Should Match Schema    ${response}    error.schema.json
    Response Field Should Be    ${response}    code    invalid_credentials

Missing Bearer Token
    ${response}=    Get Request    /users    use_auth=${False}
    Response Status Should Be    ${response}    401
    Response Field Should Be    ${response}    code    unauthorized

Invalid Bearer Token
    Use Invalid Token
    ${response}=    Get Request    /users
    Response Status Should Be    ${response}    401
    Response Field Should Be    ${response}    code    unauthorized

Customer Cannot List Users Or Read Another Account
    ${forbidden}=    Get Request    /users    role=customer
    Response Status Should Be    ${forbidden}    403
    Response Field Should Be    ${forbidden}    code    forbidden
    ${user}=    Provision Customer    Private Owner
    Login Created Customer    ${user}[email]
    ${account}=    Open Checking Account
    ${hidden}=    Get Request    /accounts/${account}[id]    role=customer
    Response Status Should Be    ${hidden}    403
    Response Should Match Schema    ${hidden}    error.schema.json

Missing Field And Wrong Type
    ${missing}=    Post User Missing Password
    Response Status Should Be    ${missing}    422
    Response Should Match Schema    ${missing}    error.schema.json
    Response Field Should Be    ${missing}    code    validation_error
    ${typed}=    Post User With Numeric Name
    Response Status Should Be    ${typed}    422
    Response Field Should Be    ${typed}    code    validation_error

Unknown User And Duplicate Email
    ${missing_user}=    Get Request    /users/does-not-exist    role=admin
    Response Status Should Be    ${missing_user}    404
    Response Field Should Be    ${missing_user}    code    not_found
    ${created}=    Provision Customer    Unique Person
    ${duplicate}=    Post Duplicate Email    ${created}[email]
    Response Status Should Be    ${duplicate}    409
    Response Field Should Be    ${duplicate}    code    conflict

Boundary Query Values And Unsupported Method
    ${zero_page}=    Create Dictionary    page=${0}    page_size=${20}
    ${page}=    Get Request    /users    role=admin    params=${zero_page}
    Response Status Should Be    ${page}    422
    Response Field Should Be    ${page}    code    validation_error
    ${huge}=    Create Dictionary    page=${1}    page_size=${101}
    ${size}=    Get Request    /users    role=admin    params=${huge}
    Response Status Should Be    ${size}    422
    ${method}=    Post Request    /health    use_auth=${False}
    Response Status Should Be    ${method}    405
    Response Should Match Schema    ${method}    error.schema.json
    Response Field Should Be    ${method}    code    method_not_allowed

Schema Mismatch Is Rejected
    ${body}=    Create Dictionary    status=ok    extra=nope
    ${bad}=    Create Dictionary    body=${body}
    Run Keyword And Expect Error    *health.schema.json*    Response Should Match Schema    ${bad}    health.schema.json
