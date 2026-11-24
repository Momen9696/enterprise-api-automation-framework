"""Account keywords owned by the dynamic customer session."""

*** Settings ***
Resource    common.resource

*** Keywords ***
Open Isolated Checking Account
    ${user}=    Provision Customer
    Login Created Customer    ${user}[email]
    ${account}=    Open Checking Account
    RETURN    ${user}    ${account}
