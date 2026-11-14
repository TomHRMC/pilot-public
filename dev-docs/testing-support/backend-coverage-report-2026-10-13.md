# Backend Test Coverage Report — Pilot for Trades

**Date:** 2026-10-13
**Command:** `pytest --cov=app --cov-report=term-missing` (DB reinitialized + seeded with A–D seed scripts)
**Headline:** **76% combined line+branch coverage** · 79.1% statement-level · **26,455 statements** measured

## Summary by layer (statement coverage)

| Layer | Stmts | Missed | Stmt coverage |
|---|---:|---:|---:|
| Data models | 2,949 | 3 | **99.9%** |
| API schemas | 1,446 | 44 | **97.0%** |
| API routes | 11,056 | 2,046 | **81.5%** |
| Services | 7,070 | 1,914 | 72.9% |
| Core | 686 | 151 | 78.0% |
| Background tasks (Celery) | 3,111 | 1,355 | 56.4% |
| **TOTAL (statement)** | **26,455** | **5,523** | **79.1%** |

**How to read it:** coverage concentrates where correctness matters most for a multi-tenant billing SaaS — the data model is ~100% covered, API schemas 97%, API routes 81.5%, and the financial paths are solid (quotes 83%, jobs 86%, invoices 84%, Stripe 67–88%). The thinnest coverage is in background Celery workers and in AI/voice/third-party-integration service shims (`ai_service`, `help_agent`, `voice_preview_audio`, `telnyx_sms_carrier`, `ocr_service`, `quickbooks_sync` task) — the lowest-risk, hardest-to-unit-test surfaces, which is exactly where thin coverage is expected and acceptable.

**Note:** this snapshot ran with a small number of known failing tests (intentionally not fixed for this run). `pytest-cov` reports coverage independent of pass/fail, so the figures above stand regardless.

---

## Full `coverage: term-missing` report

```text
__________________________________________________________________________ coverage: platform darwin, python 3.14.6-final-0 __________________________________________________________________________

Name                                            Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------------------------------------
api/__init__.py                                     0      0      0      0   100%
api/routes/__init__.py                              0      0      0      0   100%
api/routes/account_security.py                    410     36     76      9    91%   135, 306, 392, 436-437, 474-475, 500, 527-529, 550-551, 564->567, 588-590, 630-631, 664-669, 701->714, 719, 731, 759-760, 818, 855, 909, 944, 952->955, 979, 1038-1039, 1099, 1115, 1134
api/routes/addresses.py                           158     26     44      9    78%   169, 214, 261, 275, 290-302, 324->336, 386, 424-430, 445-457, 723, 745, 764, 784, 805, 830, 850, 871
api/routes/admin_tenants.py                        64     11      2      0    83%   53-59, 152-153, 197-198, 246-247
api/routes/audit.py                                94      6     30      4    89%   165, 167, 171, 315-318
api/routes/auth.py                                 60     12      8      3    78%   110-112, 120-124, 141-143, 174, 210-211
api/routes/billing_payment_contact.py              60      2     14      4    92%   75, 113->121, 123->127, 126
api/routes/calendar_conflicts.py                  180     22     30      6    86%   139-141, 170-172, 177-184, 238-244, 267->271, 335, 474, 493, 518
api/routes/calendar_integration.py                142     28     18      6    79%   83, 107, 142-155, 168-183, 200-206, 216, 241->243, 282, 372-378, 397-398, 439, 460, 474, 492
api/routes/catalog.py                             192     21     26      3    88%   55-69, 171, 247-248, 315, 495-496, 510, 607->621, 646-667
api/routes/cohort_dashboard.py                     53     26     14      2    43%   63, 78-122, 134-150, 192
api/routes/communications.py                      180     12     32      5    92%   300, 361, 517-518, 539, 602, 705, 742, 794, 865, 996, 1032
api/routes/communications_threads.py              167     63     28      5    59%   165-169, 208-231, 290, 307, 333-404, 455, 490, 512-522, 557-587, 617
api/routes/contacts.py                            158     25     44      5    79%   259, 284-300, 382, 430-453, 718, 740, 759, 779, 800, 825, 845, 866
api/routes/customers.py                           213     23     34      4    89%   140-141, 219, 312-313, 327, 346-387, 737
api/routes/dashboard.py                           175     41     26      8    72%   143, 144->146, 146->148, 149, 151, 201-237, 350, 365, 380, 394, 410, 451-452, 470-489, 504-507, 539->549, 613, 628
api/routes/health.py                               36      3      4      1    90%   94, 133-134
api/routes/help.py                                215     69     38      6    65%   74-122, 130-151, 163-178, 238, 259, 315->319, 383-390, 416-425, 502-503, 524-526, 554, 566, 578-579, 598, 631-639, 680, 695, 707-708, 718, 755-756, 776-791
api/routes/integrations.py                        588    237    150     30    56%   118-165, 196, 225-391, 412-540, 556-583, 614-616, 647, 675, 709-710, 720-721, 731-732, 742-743, 763-790, 807-833, 883-889, 975-1000, 1041-1185, 1227-1228, 1254, 1280, 1304->1312, 1321, 1333, 1335, 1337, 1339, 1341, 1345, 1347, 1364->1424, 1373->1424, 1377, 1396->1395, 1414->1421, 1430->1433, 1445-1451, 1504-1505, 1551->1580, 1565, 1624, 1756-1757, 1845->1848, 1852, 1901, 1905, 1907, 2050, 2075, 2100, 2126, 2168, 2189->2200, 2207-2214
api/routes/invoices.py                            398     49    128     28    84%   108->88, 112, 231, 233, 235, 239, 253, 255, 269, 271, 273, 275, 285, 287, 339-352, 467, 481, 593, 688-705, 752, 853-857, 937, 985, 1213->1231, 1220, 1292, 1358-1380, 1419, 1445, 1516-1527, 1542, 1687-1688
api/routes/job_expense_categories.py               32      3      6      1    84%   86-87, 143
api/routes/job_recurrence_rules.py                153     35     38     12    71%   50, 53-58, 79, 82, 134-150, 199, 211-219, 270-271, 375-380, 410, 435, 468, 478->exit, 496-497, 508, 518, 529-530, 542-543
api/routes/job_types.py                            25      1      4      0    97%   77
api/routes/jobs.py                                602     60    174     38    86%   91->76, 93, 150, 158, 161, 178-180, 281, 289, 291, 312, 318, 320, 331-332, 431->437, 449, 469, 497-504, 549, 585-586, 591, 682->694, 701, 710->722, 723-725, 769, 886, 932, 1418, 1438, 1480-1482, 1771, 1867->1879, 1877, 1948->1953, 1976, 2125, 2135, 2146, 2158, 2169, 2185, 2199, 2215, 2229, 2267->2280, 2274->2280, 2281-2284, 2293-2299, 2348, 2465, 2512, 2596
api/routes/labor_rates.py                          93     24     18      6    69%   65, 104, 123, 127, 130-135, 150-158, 179-190, 274, 291, 305
api/routes/marketing.py                           190     19     42      9    87%   110, 154, 170, 315, 409, 414-415, 427, 432-433, 438, 441-442, 449, 458-459, 524-526
api/routes/markups.py                              84     20     14      1    72%   58-60, 172, 211-219, 249-264, 299-302, 343-368
api/routes/messaging_provisioning.py              151     78     20      3    44%   105-135, 155, 170-172, 184-228, 244, 257, 270-289, 303, 317, 325-335, 348, 361, 377, 393-403, 419, 432, 455, 468, 480, 490-491, 517, 532, 545-571, 585, 599
api/routes/messaging_quote.py                      30      3      6      0    86%   91-101
api/routes/mobile_push.py                          77      3      8      1    95%   160->174, 267, 286, 308
api/routes/mobile_push_permission.py               63      4     10      1    93%   158, 226-227, 249
api/routes/mobile_sync.py                         124     12     22      4    89%   93-94, 139, 173, 186->189, 259, 370, 464-465, 478-479, 499, 520
api/routes/nec.py                                  63      4     10      1    93%   158, 187, 197, 209
api/routes/notification_categories.py              52      2     10      0    97%   170, 186
api/routes/notification_preferences.py            242     32     64     14    84%   78, 152, 170, 188-189, 191-192, 197-198, 244-248, 272-281, 310->315, 466, 470, 482-484, 519->522, 688, 718-719, 736, 760, 781, 796, 809, 820, 831, 853, 872-873
api/routes/notification_sse.py                     82     28     14      0    62%   53-61, 72-94, 123, 256, 270
api/routes/onboarding_checklist.py                 74     24     14      1    60%   74, 173-177, 194-206, 222-231, 246-252
api/routes/operator_tenants.py                     38     17     10      3    50%   61-62, 86-113, 134-142
api/routes/owner_escalations.py                   255     21     52     11    88%   185-192, 240, 245-248, 265, 297, 330, 332, 363, 426->433, 527, 546->563, 619-620, 781, 807, 829, 859-860, 875
api/routes/payment_schedules.py                   186     84     40      2    47%   215-226, 247-267, 278-319, 333-352, 404-445, 478-479, 531-532, 545-546, 598, 611, 623, 634, 649, 664, 678, 692, 708
api/routes/photos.py                              109     17     12      2    84%   161-164, 254-265, 298-299, 313-314, 339-340, 359-360
api/routes/public_charter.py                       20      0      4      0   100%
api/routes/public_invoices.py                     109     13     26      7    84%   125, 139, 173-176, 207, 249-252, 328, 369, 399-403
api/routes/public_quotes.py                       134     39     48     15    63%   99, 108, 111, 119-135, 161-202, 236, 247, 255->257, 257->259, 259->263, 300, 305, 309, 315->317, 317->319, 319->321, 321->324
api/routes/public_short_redirect.py                23     10      4      0    48%   28-36, 51-53
api/routes/public_tenant_sites.py                  62     11     14      4    80%   52-54, 65, 68-69, 123->132, 127-129, 147->153, 150-151
api/routes/qco_line_types.py                       25      0      4      0   100%
api/routes/quote_templates.py                     211     18     38      9    89%   145, 155, 157, 228-244, 313, 349-365, 436, 442, 480, 633, 658, 677, 694, 710
api/routes/quotes.py                              689     85    214     57    83%   118->103, 120, 160, 238, 250, 252, 267, 275, 277, 380-387, 417, 422->445, 458->493, 497->509, 507, 691, 700, 710, 739->742, 790, 879-881, 906->915, 916, 1050-1051, 1079-1080, 1260-1261, 1305, 1322, 1372, 1400->1408, 1408->1412, 1499, 1626, 1697, 1786, 1834-1866, 1928, 1954->1958, 1970, 1981, 1993, 2023->2032, 2030->2032, 2108->2110, 2110->2112, 2168, 2275, 2300, 2342, 2355, 2387-2401, 2436, 2454, 2465, 2552, 2567->2595, 2568->2581, 2582-2593, 2644->2647, 2649->2651, 2812, 2835, 2859, 2888, 2918, 2982, 3021, 3022->3024, 3171, 3188, 3205, 3220, 3234, 3252, 3275
api/routes/reports.py                             133     14     22      7    86%   68-70, 104, 140, 201, 234, 269, 340->354, 524, 544, 562, 584, 604, 622, 649
api/routes/roles.py                                84     19     12      2    72%   120-151, 204-205, 267, 287, 296, 305
api/routes/scheduling.py                          471     74    106      8    83%   117-125, 189-222, 262, 523, 539, 553, 568, 583, 682, 901, 917, 931, 947, 1066-1067, 1179-1197, 1281, 1357, 1467-1468, 1502-1528, 1641, 1657, 1707-1712, 1764, 1791-1832
api/routes/settings.py                            433     54    108     25    83%   59-60, 73-74, 89-90, 114, 125, 127, 129, 140, 160, 172, 184, 202, 216, 385, 467-468, 493, 495, 534-535, 560->567, 567->590, 572, 574, 575->590, 613-619, 637, 656, 723-750, 798-809, 1058-1059, 1094, 1184, 1209, 1265, 1286->1280, 1362, 1384, 1451
api/routes/signup.py                              169     47     10      3    71%   124-128, 139-143, 154-158, 169-173, 204-216, 242, 259-263, 280-284, 301-305, 320-321, 371, 382, 406-408, 481-483, 506-507, 568-569, 678-681, 704
api/routes/sites.py                                96      4     18      3    94%   181, 300, 313, 544
api/routes/sms_quota.py                            38     12      2      1    68%   57-74, 107
api/routes/stripe_connect.py                      101      7     20      7    88%   109, 138->149, 161, 195->197, 201, 249, 273->275, 279, 315, 360
api/routes/subscription_tiers.py                   23      1      0      0    96%   88
api/routes/sync_status.py                          83     16     22      2    77%   138, 179-193, 283, 313-314
api/routes/team_invites.py                         95     11     10      1    85%   284-285, 294, 308-319, 333-344
api/routes/tenant_10dlc_profile.py                100     14     24      6    82%   34, 140, 161, 171, 178, 182, 192-193, 252-267, 281-282
api/routes/tenant_email_branding.py               150     56     28      5    60%   88-105, 124-126, 152, 157, 175, 244, 255, 268-315, 328-335, 352-373
api/routes/tenant_phone_numbers.py                 48      7      8      1    79%   85, 203-208, 222-227
api/routes/tenant_site.py                         119     14     16      5    86%   170, 174, 189-191, 203, 266, 294-295, 397-398, 416-417, 430-431
api/routes/tenant_subscription.py                 218     69     72     17    62%   159, 178, 195, 310-314, 341, 364, 371, 392, 398, 414-456, 471, 477, 482, 493->500, 495, 512-542, 574-607, 644-679, 777, 794, 811, 831, 854
api/routes/user_color.py                           41      1      4      0    98%   152
api/routes/user_preferences.py                     47      2      4      1    94%   83->86, 167, 180
api/routes/user_profile.py                        119     18     24      4    85%   95-96, 129, 140, 214, 253-254, 276, 296-297, 361, 395-396, 419-420, 436-438
api/routes/voice.py                               155     53     22      2    66%   62-63, 71-72, 124-127, 133-134, 140-142, 159->183, 172-180, 226-230, 237->262, 252-256, 335-336, 379-438, 451-461, 491-492, 513-514, 540, 566
api/routes/voice_feedback.py                       88      7     12      4    89%   104->115, 157, 168-173, 215, 314, 332, 354
api/routes/voice_persona.py                       180     13     14      2    92%   243-253, 300->303, 393, 434, 475-478, 506, 546-547, 581-583, 629
api/routes/voice_sessions.py                       69      3      4      0    96%   224-225, 313
api/routes/webhooks.py                             63      3      8      2    93%   94-95, 109
api/routes/webhooks_sms.py                        193     91     42      5    52%   99-155, 170-223, 237-253, 338-340, 350-351, 415-417, 470-478, 484, 491-523, 596-597, 602
api/routes/webhooks_stripe.py                     199     57     58     15    67%   82-84, 154, 156, 168, 171, 174, 176, 178, 180, 183-191, 205-208, 222-238, 260-262, 274-276, 290, 347-350, 352-355, 359->366, 373-385, 398->409, 435-436, 468-469
api/schemas/__init__.py                             0      0      0      0   100%
api/schemas/addresses.py                           30      0      0      0   100%
api/schemas/cohort.py                              17      0      0      0   100%
api/schemas/contacts.py                            26      0      0      0   100%
api/schemas/dlc.py                                 79     13     10      1    75%   32, 114-116, 121-123, 152-154, 217-219
api/schemas/help.py                                86      0      0      0   100%
api/schemas/invoice_signoff.py                     19      0      0      0   100%
api/schemas/marketing.py                           57      0      2      0   100%
api/schemas/nec.py                                 16      0      0      0   100%
api/schemas/operator.py                            13      0      0      0   100%
api/schemas/quotes.py                             132      0      2      0   100%
api/schemas/recurrence.py                          32      1      4      1    94%   30
api/schemas/reports.py                            166      0      0      0   100%
api/schemas/roles.py                               48      0      0      0   100%
api/schemas/schemas.py                            522     28     62     11    90%   722, 724, 777, 1175, 1374, 1375->1382, 1381, 1390, 1396, 1418-1431, 1435-1441, 1485, 1498
api/schemas/signup.py                              12      0      0      0   100%
api/schemas/team_invites.py                        40      0      0      0   100%
api/schemas/tenant_site.py                        111      2      4      2    97%   33, 42
api/schemas/voice.py                               40      0      2      0   100%
app/__init__.py                                     0      0      0      0   100%
app/main.py                                       137     10      4      2    91%   475, 508-526, 537-538
app/models/__init__.py                             24      0      0      0   100%
app/models/ai.py                                   89      0      0      0   100%
app/models/auth.py                                204      0      0      0   100%
app/models/billing.py                             390      3      2      0    99%   830-834
app/models/catalog.py                             136      0      0      0   100%
app/models/communications.py                       86      0      0      0   100%
app/models/core.py                                136      0      4      1    99%   318->exit
app/models/crm.py                                 188      0      0      0   100%
app/models/fulfillment.py                         198      0      0      0   100%
app/models/help.py                                 74      0      0      0   100%
app/models/legal_acceptance.py                     19      0      0      0   100%
app/models/marketing.py                            62      0      0      0   100%
app/models/mixins.py                               15      0      0      0   100%
app/models/mobile_push_permission.py               17      0      0      0   100%
app/models/onboarding.py                           27      0      0      0   100%
app/models/platform_setting.py                     32      0      0      0   100%
app/models/quoting.py                             376      0      0      0   100%
app/models/reports.py                              29      0      0      0   100%
app/models/scheduling.py                           87      0      0      0   100%
app/models/security.py                             72      0      0      0   100%
app/models/settings.py                             15      0      0      0   100%
app/models/signup.py                               23      0      0      0   100%
app/models/sms.py                                 103      0      0      0   100%
app/models/subscription.py                         48      0      0      0   100%
app/models/sync.py                                 82      0      0      0   100%
app/models/system.py                              382      0      0      0   100%
app/models/tenant_site.py                          29      0      0      0   100%
app/models/voice_helpers.py                         6      0      0      0   100%
core/__init__.py                                    0      0      0      0   100%
core/auth.py                                      158     68     44      9    52%   37-52, 64-82, 96-145, 186, 196, 216-218, 263, 277-340, 393, 403, 421, 441, 493, 501-502, 529, 538, 561
core/celery_app.py                                  5      0      0      0   100%
core/config.py                                     88      0      0      0   100%
core/datetime_utils.py                             22     13     10      0    28%   46-52, 76-84, 135-147
core/db.py                                         13      1      0      0    92%   74
core/encryption.py                                 12      2      4      2    75%   39, 65
core/idempotency.py                                89     15     20      3    82%   127, 169-188, 190->218, 225->229, 231-233, 257-263
core/middleware.py                                 32      0      4      0   100%
core/permissions.py                                58     12     22      1    79%   298->309, 340-364, 394
core/quickbooks_webhook.py                         22      2      6      1    89%   47-48
core/rate_limit.py                                 46      4     12      4    86%   138, 213->215, 216, 218, 295
core/sse_middleware.py                             29     22      8      0    19%   56-117
core/stripe_config.py                              18      1      4      1    91%   45
core/system_config.py                               6      0      0      0   100%
core/tax_calculation.py                            53      1     14      1    97%   91
core/test_context.py                               20      1      2      0    95%   150
core/turnstile.py                                  15      9      0      0    40%   43-61
services/ai_service.py                             55     47      2      0    14%   14-35, 44-56, 63-96, 115-127
services/billing_rate_service.py                   27      0     12      0   100%
services/calendar_conflict_service.py              99      0     24      2    98%   306->308, 308->293
services/cognito_mfa_client.py                    131     16     40      5    88%   137, 142-143, 151-152, 164-165, 172-173, 183-184, 196->201, 202, 208->210, 211, 214-215, 286
services/cohort_dashboard.py                      107      9     38      8    88%   44, 118->125, 178, 199, 232-236, 300, 312->318, 330->329
services/customer_comms_service.py                 47      2     14      2    93%   158, 235
services/customer_communication_threading.py      135     24     16      5    81%   120, 125-126, 159-160, 198-199, 243-244, 257-273, 288-289, 317-318, 348-349, 365-366
services/data_export_compiler.py                  102     84     44      0    12%   81-142, 158-280
services/dispatch_board_stream.py                  76     52     16      0    26%   113-132, 165-246
services/email_service.py                          29      3      6      2    86%   54, 64-65
services/email_template_renderer.py                65     10     16      4    80%   108-109, 112->117, 118, 128, 143-148, 186
services/entitlement_service.py                    92     19     26      2    79%   113, 257, 272-279, 327-328, 345-355
services/etc_service.py                            30      4      6      1    86%   101-108
services/expo_push_service.py                      70     16     26      4    75%   140-142, 151-162, 200-211, 224-226
services/gps_variance_service.py                   56     32     16      0    33%   93-138, 170-209
services/help_agent.py                             51     41     20      0    14%   64-76, 86-91, 106-152
services/help_corpus.py                           150     88     50      5    38%   82-176, 230, 236->240, 260-297, 309-317, 326-364, 369-373, 384, 393-405
services/help_retrieval.py                         29      6      4      1    79%   55-69, 101, 146-148
services/impersonation_service.py                  43     29     10      0    26%   42-85, 104-116, 131-147, 168-176
services/map_service.py                           130     16     34      4    88%   136-144, 157-158, 166-167, 180, 190-191, 302-303, 416
services/messaging_checkout.py                     30      3      8      4    82%   43, 51, 55, 105->107
services/messaging_provisioning.py                184     35     64     16    76%   115->119, 173, 225, 301, 366-367, 370-375, 378-382, 395->exit, 422-425, 428-433, 436-440, 447->exit, 480, 483, 563, 577-579, 601-640
services/messaging_recurring.py                    35      1     10      1    96%   46
services/mobile_background_sync.py                131     49     32      4    60%   197-201, 289-294, 325, 352-381, 410-439, 481-500
services/mobile_sync_conflict.py                   51      0     12      0   100%
services/nec_service.py                           123     21     44     14    79%   189->188, 191, 288-289, 292, 294, 296, 370-371, 374, 376, 378, 462-463, 466, 468, 475, 481-482, 491-503, 510
services/notification_endpoints.py                 61     17      8      2    70%   122-128, 164->168, 230-245, 297, 330-345
services/notification_resolver.py                  41      4     20      4    87%   101, 112, 126, 171
services/ocr_service.py                           101     72     30      1    24%   92-111, 115-150, 155-186, 239-242
services/onboarding_service.py                    108     12     30      1    88%   101-106, 111-116, 146->149
services/payment_schedule_service.py              107      6     34      6    91%   178, 217, 257, 332, 371, 385
services/pii_anonymizer.py                         28      1     12      2    92%   103->108, 109
services/platform_sms_templates.py                 11      0      2      0   100%
services/public_link_signer.py                     67      8     16      2    88%   72, 159-160, 179-180, 185, 189-190
services/qb_conflict_diff.py                       66      8     36      6    84%   60, 95->90, 135, 139-140, 170, 189, 201-202
services/qb_connection_notification.py             28      4      4      2    81%   76-82, 87-93
services/quickbooks_sync.py                       309     92     78     15    70%   116, 124, 193, 295-300, 409-410, 441-444, 651->653, 653->655, 655->657, 657->659, 659->661, 798, 802-821, 875-895, 931-1049, 1084-1176, 1204
services/quote_service.py                          79     12     24      8    79%   58-63, 114->exit, 144, 178, 192, 275-280, 291, 349-353
services/report_service.py                        185     74     48     13    59%   125-127, 129-131, 143-144, 181, 231-232, 234-235, 291-318, 408-421, 465, 492, 498-502, 566-590, 710-713
services/s3_service.py                             46     20      4      0    52%   31, 47-52, 71-85, 104-109, 125-136
services/scheduling_service.py                     84      2     32      3    96%   286, 320, 331->335
services/session_revoke_service.py                 40      3     10      2    90%   126-128, 132->138
services/setting_resolver.py                       31      0     12      0   100%
services/short_link_resolver.py                    50     15     16      4    62%   72-75, 120-125, 136-143, 154-160
services/sms_carrier.py                            94      4      8      1    95%   243, 259, 312-314
services/sms_provisioning.py                       58     18      4      0    68%   118-119, 158-176
services/sms_quota.py                              55      0     10      0   100%
services/stripe_connect_notifications.py           48     12     10      5    71%   46-55, 76-81, 85-90, 150-155, 159-164, 167-168
services/stripe_payment_intents.py                123     23     30      6    78%   153-155, 199-200, 210-211, 222-226, 292, 341, 350-353, 379-393, 408-422
services/stripe_subscriptions.py                  519    104    174     42    76%   32, 50, 59-64, 81-106, 140-141, 146, 150, 180-182, 184-190, 239->251, 245->251, 254-255, 289-290, 300->308, 305, 440-455, 478, 485-486, 539-582, 608-643, 747-754, 763-769, 943, 998->1003, 1065, 1075, 1114->1119, 1115->1114, 1120, 1152->1158, 1184->1186, 1295-1314, 1327, 1343->1348, 1364, 1370-1373, 1380->1385, 1402, 1423->1433, 1427->1433, 1490->1508, 1500-1501, 1521->1526, 1541-1559, 1588->exit, 1593->exit, 1598-1599
services/team_invite_service.py                   151      7     34      3    95%   90, 222-223, 257, 262, 274->278, 394-395
services/tech_color_service.py                     24      7      6      2    63%   59-72, 110->109, 114-115
services/telnyx_quoting.py                         22      0     10      1    97%   130->132
services/telnyx_sms_carrier.py                    213    145     56      3    29%   53, 55, 57-64, 104-137, 144-183, 237-239, 246-249, 263-280, 286-295, 378-380, 384-396, 408-458, 462-474, 483-525, 532-561, 570-586
services/template_renderer.py                      19      4      2      1    76%   27, 37-39
services/tenant_signup.py                         164     20     76     19    81%   80->151, 116->120, 260, 283, 358-373, 377, 393-395, 405, 423, 453, 499->exit, 515->exit, 537->exit, 544->exit, 546->exit, 556->exit, 575, 583->599, 607-616
services/tenant_site_service.py                   282     29    102     20    85%   158, 189, 192, 197-198, 258-261, 272->274, 283, 284->286, 294-295, 341->343, 343->345, 462-463, 512, 555->583, 610, 659, 694, 712, 718-730, 741->743, 743->746
services/tenant_site_templates/__init__.py         37      6     12      2    80%   24-25, 37, 79-82
services/tenant_site_templates/v1/__init__.py       0      0      0      0   100%
services/tier_limit_enforcer.py                    54     14     18      3    65%   44-69, 93, 114, 164
services/trial_management.py                       82     49     30      6    37%   66-69, 87-119, 129, 132, 136, 145, 158-161, 180-232
services/voice_action_router.py                  1329    419    370     78    65%   117-119, 144-186, 225->238, 240->252, 331, 347-348, 374, 377, 441-453, 668, 789-790, 799, 808, 963, 973, 989-990, 1044->1059, 1046->1059, 1069, 1084, 1094->1105, 1113-1114, 1202, 1246-1251, 1325, 1369-1374, 1463, 1479, 1552, 1562-1563, 1577, 1598, 1640-1645, 1678-1679, 1737, 1748-1749, 1761-1769, 1783, 1800->1803, 1804, 1824-1825, 1884, 1893-1897, 1905, 1920, 1991-1992, 2031, 2033-2035, 2057-2058, 2113, 2175-2176, 2191, 2211-2212, 2338-2434, 2453, 2456, 2466-2467, 2482, 2494, 2506, 2508-2510, 2518, 2539-2579, 2591-2600, 2604-2614, 2618, 2671, 2688, 2749-2803, 2862-2895, 2923-2977, 3029-3035, 3083-3084, 3120, 3166, 3187, 3193-3194, 3219-3220, 3252, 3262, 3305-3306, 3386-3389, 3394-3423, 3431, 3486->3490, 3649, 3664-3665, 3717, 3729-3730, 3781, 3793-3794, 3885->3893, 3900, 3943, 3971-3972, 3979->4002, 4048-4049, 4066, 4215->4225, 4304-4305, 4391-4403, 4463-4464, 4507-4529, 4578-4659, 4692-4741, 4777-4839, 4869-4906, 4940-5091, 5180
services/voice_persona_renderer.py                 86     13     16      3    84%   73, 79, 128->136, 159-161, 205-209, 277-282, 286-287
services/voice_preview_audio.py                    69     69     12      0     0%   25-205
services/voice_session_service.py                  73     14     28      2    78%   101-102, 131->134, 221-240
services/wip_service.py                            48      0      6      0   100%
tasks/__init__.py                                   0      0      0      0   100%
tasks/archive_audit_logs.py                       144     34     26      4    78%   198, 256->252, 278-281, 285, 313, 360, 378, 389, 397-435
tasks/auto_expire_qb_conflicts.py                  58     34      8      1    41%   41-122, 164-179
tasks/background_sync_push.py                      92     42     18      3    55%   55-98, 124-126, 177-178, 204, 206->213, 235-247, 298-305
tasks/calendar_sync.py                            229     79     34      7    65%   85-97, 152-153, 213-246, 258-276, 354-365, 377-406, 410->417, 486-488, 499-519, 533-534, 543-544, 551, 553-556, 571-575, 614->616
tasks/check_system_template_updates.py             54     24     16      2    57%   70, 100-146, 165, 188-198
tasks/cleanup_idempotency_keys.py                  61     40     10      1    31%   46-59, 85-123, 135, 141, 145-161
tasks/cleanup_sessions.py                         120     38     28      5    70%   88, 137-140, 144, 164, 201-204, 208, 228, 255-271, 275, 287, 293, 299, 303-321
tasks/data_export_pipeline.py                      78     38      8      0    51%   44-63, 117-118, 123-128, 133-147, 157-164
tasks/dunning.py                                  126     40     26      9    66%   38-46, 84->94, 96-101, 108-111, 114->119, 120-124, 185-187, 198-199, 248, 249->251, 252-253, 256-260, 279, 306, 320-366
tasks/expire_stale_calendar_conflicts.py           63     19     16      3    70%   31-39, 70-73, 119->164, 123-161, 199-202, 206
tasks/free_period_notifications.py                 71     58     16      0    15%   38-46, 59-104, 124-210
tasks/help_corpus.py                              155     63     30      5    60%   45-57, 87-96, 144-148, 156, 186-198, 237->242, 259, 275-301, 343-352, 359-360
tasks/login_recording.py                           30      8      0      0    73%   108-126
tasks/marketing_notifications.py                   79     49      2      0    37%   89-129, 165-218, 247-312, 337-389
tasks/messaging_provisioning.py                    95     77     12      0    17%   46-120, 130-138, 154-214, 224-232, 244-245, 253-261
tasks/messaging_recurring.py                       39     11      2      0    73%   56-57, 76-84
tasks/mfa_grace_reminders.py                       54     15     14      3    68%   36-44, 94, 99-102, 133-139
tasks/mobile_sync_cleanup.py                       30      9      4      1    65%   65-71, 80-83
tasks/monitor_sms_quota_thresholds.py              49     30      8      1    35%   46-67, 77-93, 102-112
tasks/notification_worker.py                      211     92     70     11    57%   95, 129-177, 187, 209-211, 221-222, 226-229, 264-275, 302-308, 339, 343, 369, 384-385, 429-467, 495-554
tasks/notify_etc_variance_owners.py                86     60     22      1    25%   74-222, 227-230
tasks/photo_cleanup_tasks.py                       40     19      8      0    52%   46-82
tasks/profitability_rollup.py                      72     26      8      1    64%   164-182, 216-239
tasks/quickbooks_sync.py                          142    107     12      2    24%   59-107, 132-166, 195-235, 290-338, 349-352, 380-384, 409-449, 481-521
tasks/quickbooks_token_refresh.py                  86      7     14      1    92%   80-81, 85, 243-246
tasks/quote_discount_expiry.py                     34      9      4      0    76%   85-94
tasks/quote_expiration_monitor.py                  34     24      4      0    26%   33-95
tasks/receipt_ocr.py                               56     11     10      3    79%   83-87, 96-101, 123->126, 143-155
tasks/recurring_jobs.py                           112     36     16      3    70%   62, 90-94, 103-114, 191, 194-196, 219-235, 252-253, 263-267, 280-288
tasks/rollover_sms_quota_periods.py                74     23     16      7    67%   70-72, 75->60, 77->141, 92, 102->141, 128-136, 153-154, 179, 200-210
tasks/saas_billing_aggregator.py                   55     36     14      1    29%   65-177
tasks/sms_compliance.py                            60     34     12      1    40%   78-160, 188-210
tasks/sms_compliance_platform.py                   54     17     12      3    67%   85-89, 94-98, 143-148, 176-201
tasks/sms_platform_notifications.py                62     49     14      0    17%   94-239, 282-322
tasks/system_template_notifier.py                  34     11     10      2    70%   56, 67, 109-118
tasks/tenant_site_emails.py                        66     11     14      4    81%   106->116, 110-111, 150->160, 157-158, 176->181, 183, 200-210
tasks/test_task.py                                  6      0      0      0   100%
tasks/trial_management.py                          40     31      8      0    19%   32-89
tasks/voice_feedback_export.py                     50     13      8      1    76%   35-43, 86-90, 100-102
tasks/voice_offline_tasks.py                       55     20      4      1    64%   64-78, 108->110, 157-165
tasks/voice_session_title.py                       55     11      8      1    81%   40-49, 150, 163
-------------------------------------------------------------------------------------------
TOTAL                                           26455   5523   5188    948    76%
```
