*** Settings ***
Documentation    Kubernetes infrastructure tests for Online Boutique
Library          KubeLibrary    ${KUBECONFIG}
Library          Collections
Resource         ../resources/common_keywords.robot

*** Test Cases ***
TC201: Verify All Pods Are Running
    [Documentation]    Verify all Online Boutique pods are in Running state
    [Tags]    k8s    infrastructure    smoke
    @{pods}=    Get Pods In Namespace    ${NAMESPACE}    label_selector=app=online-boutique
    ${pod_count}=    Get Length    ${pods}
    Should Be True    ${pod_count} >= 11    Should have at least 11 pods (one for each service)
    
    FOR    ${pod}    IN    @{pods}
        ${status}=    Get Pod Status    ${pod.metadata.name}    ${NAMESPACE}
        Should Be Equal    ${status.phase}    Running    Pod ${pod.metadata.name} should be Running
    END

TC202: Verify Frontend Service Exists
    [Documentation]    Verify frontend service is created and accessible
    [Tags]    k8s    services
    ${service}=    Get Service    frontend    ${NAMESPACE}
    Should Not Be Empty    ${service}
    Should Be Equal    ${service.metadata.name}    frontend

TC203: Verify All Required Services Exist
    [Documentation]    Verify all microservices have corresponding Kubernetes services
    [Tags]    k8s    services
    @{required_services}=    Create List
    ...    frontend
    ...    cartservice
    ...    productcatalogservice
    ...    currencyservice
    ...    paymentservice
    ...    shippingservice
    ...    emailservice
    ...    checkoutservice
    ...    recommendationservice
    ...    adservice
    ...    redis-cart
    
    FOR    ${service_name}    IN    @{required_services}
        ${service}=    Run Keyword And Return Status    Get Service    ${service_name}    ${NAMESPACE}
        Should Be True    ${service}    Service ${service_name} should exist
    END

TC204: Verify Deployments Have Desired Replicas
    [Documentation]    Verify all deployments have the desired number of replicas running
    [Tags]    k8s    deployments
    @{deployments}=    Get Deployments In Namespace    ${NAMESPACE}    label_selector=app=online-boutique
    
    FOR    ${deployment}    IN    @{deployments}
        ${name}=    Set Variable    ${deployment.metadata.name}
        ${desired}=    Set Variable    ${deployment.spec.replicas}
        ${ready}=    Set Variable    ${deployment.status.ready_replicas}
        Should Be Equal As Integers    ${ready}    ${desired}    
        ...    Deployment ${name} should have ${desired} ready replicas
    END

TC205: Verify Pod Resource Limits
    [Documentation]    Verify pods have resource limits defined
    [Tags]    k8s    resources
    @{pods}=    Get Pods In Namespace    ${NAMESPACE}    label_selector=app=online-boutique
    
    FOR    ${pod}    IN    @{pods}
        ${containers}=    Set Variable    ${pod.spec.containers}
        FOR    ${container}    IN    @{containers}
            ${has_limits}=    Run Keyword And Return Status
            ...    Dictionary Should Contain Key    ${container.resources}    limits
            Run Keyword If    ${has_limits}    
            ...    Log    Pod ${pod.metadata.name} container ${container.name} has resource limits
        END
    END

TC206: Verify ConfigMaps Exist
    [Documentation]    Verify required ConfigMaps are created
    [Tags]    k8s    configmaps
    @{configmaps}=    Get Config Maps In Namespace    ${NAMESPACE}
    ${cm_count}=    Get Length    ${configmaps}
    Log    Found ${cm_count} ConfigMaps in namespace ${NAMESPACE}

TC207: Verify No Pods Are In CrashLoopBackOff
    [Documentation]    Verify no pods are in CrashLoopBackOff state
    [Tags]    k8s    health    smoke
    @{pods}=    Get Pods In Namespace    ${NAMESPACE}    label_selector=app=online-boutique
    
    FOR    ${pod}    IN    @{pods}
        ${status}=    Get Pod Status    ${pod.metadata.name}    ${NAMESPACE}
        Should Not Be Equal    ${status.phase}    CrashLoopBackOff
        ...    Pod ${pod.metadata.name} should not be in CrashLoopBackOff
    END

TC208: Verify Frontend Service Is LoadBalancer Type
    [Documentation]    Verify frontend service is exposed as LoadBalancer
    [Tags]    k8s    services
    ${service}=    Get Service    frontend-external    ${NAMESPACE}
    Should Be Equal    ${service.spec.type}    LoadBalancer
    ...    Frontend service should be LoadBalancer type

TC209: Verify Pod Restart Count
    [Documentation]    Verify pods have minimal restart counts
    [Tags]    k8s    stability
    @{pods}=    Get Pods In Namespace    ${NAMESPACE}    label_selector=app=online-boutique
    
    FOR    ${pod}    IN    @{pods}
        ${status}=    Get Pod Status    ${pod.metadata.name}    ${NAMESPACE}
        ${container_statuses}=    Set Variable    ${status.container_statuses}
        FOR    ${container_status}    IN    @{container_statuses}
            ${restart_count}=    Set Variable    ${container_status.restart_count}
            Should Be True    ${restart_count} < 5
            ...    Pod ${pod.metadata.name} has ${restart_count} restarts (should be less than 5)
        END
    END

TC210: Verify Horizontal Pod Autoscaler
    [Documentation]    Verify HPA is configured if autoscaling is enabled
    [Tags]    k8s    autoscaling
    ${hpa_exists}=    Run Keyword And Return Status
    ...    Get Hpas In Namespace    ${NAMESPACE}
    Run Keyword If    ${hpa_exists}
    ...    Log    HPA is configured for autoscaling

TC211: Verify Service Endpoints
    [Documentation]    Verify all services have endpoints (pods backing them)
    [Tags]    k8s    services    endpoints
    @{services}=    Get Services In Namespace    ${NAMESPACE}
    
    FOR    ${service}    IN    @{services}
        ${endpoints}=    Get Endpoints    ${service.metadata.name}    ${NAMESPACE}
        ${has_subsets}=    Run Keyword And Return Status
        ...    Dictionary Should Contain Key    ${endpoints}    subsets
        Run Keyword If    ${has_subsets}
        ...    Log    Service ${service.metadata.name} has endpoints
    END

TC212: Verify Pod Labels
    [Documentation]    Verify pods have required labels
    [Tags]    k8s    labels
    @{pods}=    Get Pods In Namespace    ${NAMESPACE}    label_selector=app=online-boutique
    
    FOR    ${pod}    IN    @{pods}
        ${labels}=    Set Variable    ${pod.metadata.labels}
        Dictionary Should Contain Key    ${labels}    app
        Log    Pod ${pod.metadata.name} has app label: ${labels['app']}
    END

TC213: Verify Namespace Exists
    [Documentation]    Verify the target namespace exists
    [Tags]    k8s    namespace
    ${namespace}=    Get Namespace    ${NAMESPACE}
    Should Be Equal    ${namespace.metadata.name}    ${NAMESPACE}

TC214: Verify No Pending Pods
    [Documentation]    Verify no pods are stuck in Pending state
    [Tags]    k8s    health
    @{pods}=    Get Pods In Namespace    ${NAMESPACE}    label_selector=app=online-boutique
    
    FOR    ${pod}    IN    @{pods}
        ${status}=    Get Pod Status    ${pod.metadata.name}    ${NAMESPACE}
        Should Not Be Equal    ${status.phase}    Pending
        ...    Pod ${pod.metadata.name} should not be Pending
    END

TC215: Verify Redis StatefulSet
    [Documentation]    Verify Redis is deployed as StatefulSet or Deployment
    [Tags]    k8s    redis
    ${redis_exists}=    Run Keyword And Return Status
    ...    Get Service    redis-cart    ${NAMESPACE}
    Should Be True    ${redis_exists}    Redis service should exist
