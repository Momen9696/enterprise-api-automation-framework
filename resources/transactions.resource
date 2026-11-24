"""Transaction scenario keywords."""

*** Settings ***
Resource    accounts.resource

*** Keywords ***
Assert Status From Row
    [Arguments]    ${response}    ${row}    ${success_schema}
    ${expected}=    Convert To Integer    ${row}[expected_status]
    Response Status Should Be    ${response}    ${expected}
    IF    ${expected} == 201
        Response Should Match Schema    ${response}    ${success_schema}
    ELSE
        Response Should Match Schema    ${response}    error.schema.json
        Response Field Should Be    ${response}    code    ${row}[expected_code]
    END
