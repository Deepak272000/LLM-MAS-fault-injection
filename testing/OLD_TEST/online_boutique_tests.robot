*** Settings ***
Documentation     Smoke tests for Google Microservices Demo (Online Boutique)
Library           SeleniumLibrary
Library           RequestsLibrary

*** Variables ***
${URL}            http://localhost:8080      # Change this to your LoadBalancer IP or local address
${BROWSER}        headlesschrome

*** Test Cases ***
Frontend Home Page Should Be Accessible
    [Documentation]    Verify the frontend is up and displays the product list.
    Open Browser    ${URL}    ${BROWSER}
    Page Should Contain    Online Boutique
    Page Should Contain Element    class:product-card
    [Teardown]    Close Browser

Product Details Page Load
    [Documentation]    Verify clicking a product displays the details page.
    Open Browser    ${URL}    ${BROWSER}
    Click Element    xpath://div[contains(@class, 'product-card')][1]//a
    Wait Until Page Contains    Product Description
    Element Should Be Visible    xpath://button[@type='submit' and contains(text(), 'Add To Cart')]
    [Teardown]    Close Browser

Service Health Check (API)
    [Documentation]    Ping the frontend health check endpoint.
    Create Session    frontend    ${URL}
    ${resp}=    GET On Session    frontend    /_healthz
    Should Be Equal As Strings    ${resp.status_code}    200

*** Keywords ***
# Add custom keywords here as you expand your test suite
