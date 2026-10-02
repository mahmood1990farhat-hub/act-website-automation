# ACT cancellation/refund policy — approved 2 October 2026

Status: business rules APPROVED by Mahmood Farhat in the project conversation at
09:26 Europe/London on 2 October 2026. Website wording prepared on the unpublished
language branch; NOT a production deployment or automated-refund authorisation.

This dated approval supersedes the “Approval required” status for the cancellation,
amendment, no-show, waiting and refund decisions in section 6 of ACT Master
Operations Document v1.1 (8 September 2026). It does not approve unrelated
liability/service/safety clauses or certify legal compliance.

## Exact approved commercial decisions

- Full refund when cancellation is received at least 24 hours before confirmed pickup, including exactly 24 hours.
- Inside 24 hours: reasonable evidenced losses directly caused by cancellation, capped at the booking price, accounting for costs saved/replacement work and reasonable mitigation; refund the remainder.
- No-show assessed only after agreed waiting and documented contact attempts, using the same loss-based cap. No automatic blanket forfeiture.
- Waiting: 15 minutes ordinary pickups; 60 minutes airport pickups; measured from agreed pickup, not automatically from aircraft landing. Extra waiting charges disclosed and agreed. No new waiting-charge rate approved.
- ACT unable to provide journey: customer may accept an alternative or receive a full refund for the unprovided journey.
- Flight delays/cancellations: review and agree revised pickup; known delay is not automatically a no-show. No unlimited-waiting promise.
- Amendments subject to availability; revised price disclosed before acceptance.
- Initiate refund to original payment method within 5 working days after amount is confirmed; bank/provider credit can take longer.
- Notice uses ACT receipt time and confirmed pickup, not staff reply time. Booking reference by email, plus telephone for urgent changes.

## Publication and operational boundary

Home dictionaries now contain all nine aligned clauses in English, Arabic and
French; cancellation/flight FAQs and the existing payment subtitle are updated.
The French hardcoded-display fallback map is reconciled too. No code, fare arithmetic,
locale enabling, database records or payment/refund execution changed.

The Terms component can prioritise a backend-managed instruction PDF over the
dictionary fallback. That PDF, confirmation/email templates and any operational
cancellation handlers must be aligned before an approved publication. Do not
claim these updated JSON files replace backend PDFs or existing booking contracts.
Do not silently apply changed terms retrospectively to existing bookings.
The master DOCX itself has not been edited; this approved dated record resolves
the decision and is the checkpoint to use when synchronising that document.

## Verification

One focused content check passed for all three languages: nine aligned clauses,
24/15/60/5 thresholds and official contacts; all other dictionary fields unchanged.
Full English/Arabic dictionary shape already differs in navigation protected flags;
those pre-existing differences were inspected and left unchanged. No build/browser
rerun for this text-only preparation. Production remains unchanged; French hidden.

## Customer wording

### English

**Cancellation at least 24 hours before pickup**

If ACT receives your cancellation at least 24 hours before the confirmed pickup time, including exactly 24 hours beforehand, you receive a full refund.

**Cancellation within 24 hours**

ACT may deduct reasonable, evidenced losses directly caused by your cancellation, up to the booking price. We take reasonable steps to reduce these losses and account for costs saved or replacement work. Any remaining balance is refunded.

**Passenger no-show**

A no-show is assessed only after the agreed waiting period and documented attempts to contact the passenger. Any deduction follows the same loss-based rule as a cancellation within 24 hours and is capped at the booking price.

**Waiting periods**

The waiting period is 15 minutes for ordinary pickups and 60 minutes for airport pickups, measured from the agreed pickup time. Any charge for additional waiting must be disclosed and agreed.

**If ACT cannot provide the journey**

We offer an alternative for you to accept or a full refund for the journey that cannot be provided.

**Flight delays or cancellations**

Contact ACT with any change to your flight. We review and agree revised pickup arrangements. A known flight delay is not automatically treated as a passenger no-show.

**Booking amendments**

Changes are subject to availability. Any revised price is disclosed before you accept the change.

**Refund processing**

We initiate refunds to the original payment method within 5 working days of confirming the refund amount. Your bank or payment provider may take longer to credit the funds.

**How to cancel or amend a booking**

Email info@airportandcitytransfer.com with your booking reference. For urgent changes, also telephone +44 208 153 0303. Cancellation notice is measured from when ACT receives it, using the confirmed pickup time, not when staff reply.

**Cancellation FAQ**

Yes. If ACT receives your cancellation at least 24 hours before the confirmed pickup time, you receive a full refund. Within 24 hours, reasonable evidenced cancellation losses may be deducted, capped at the booking price and reduced for costs saved or replacement work. Changes depend on availability; any revised price requires your acceptance. Email info@airportandcitytransfer.com with your booking reference and telephone +44 208 153 0303 for urgent changes. See our Terms & Conditions for waiting, no-show and refund-processing details.

**Flight FAQ**

Contact ACT with any flight delay or cancellation so we can review and agree revised pickup arrangements. A known flight delay is not automatically treated as a passenger no-show.

**Payment notice**

Cancellation received at least 24 hours before pickup: full refund. Within 24 hours or for a no-show, reasonable evidenced losses may be deducted, capped at the booking price and allowing for costs saved or replacement work. Please read the Terms & Conditions before paying.

### Arabic

**الإلغاء قبل موعد الاستلام بـ24 ساعة على الأقل**

إذا استلمت ACT طلب الإلغاء قبل موعد الاستلام المؤكد بـ24 ساعة على الأقل، بما في ذلك قبل الموعد بـ24 ساعة تمامًا، يحق لك استرداد المبلغ كاملًا.

**الإلغاء خلال الـ24 ساعة السابقة للاستلام**

يجوز لـACT خصم الخسائر المعقولة والمثبتة الناتجة مباشرةً عن الإلغاء، بحد أقصى قيمة الحجز. نتخذ خطوات معقولة لتقليل هذه الخسائر، ونراعي التكاليف التي تم توفيرها أو العمل البديل. ويُرد إليك أي مبلغ متبقٍ.

**عدم حضور الراكب**

لا يُقيّم الحجز باعتباره حالة عدم حضور إلا بعد انتهاء فترة الانتظار المتفق عليها وتوثيق محاولات التواصل مع الراكب. ويخضع أي خصم لقاعدة الخسائر نفسها المطبقة على الإلغاء خلال الـ24 ساعة السابقة للاستلام، وبحد أقصى قيمة الحجز.

**فترات الانتظار**

فترة الانتظار هي 15 دقيقة للاستلام العادي و60 دقيقة للاستلام من المطار، وتُحسب من موعد الاستلام المتفق عليه. يجب الإفصاح عن أي رسوم للانتظار الإضافي والاتفاق عليها.

**إذا تعذّر على ACT توفير الرحلة**

نعرض عليك بديلًا لقبوله، أو نرد كامل المبلغ المدفوع مقابل الرحلة التي يتعذّر توفيرها.

**تأخر الرحلات الجوية أو إلغاؤها**

تواصل مع ACT عند حدوث أي تغيير في رحلتك الجوية، لنراجع ترتيبات الاستلام المعدّلة ونتفق عليها. لا يُعتبر تأخر الرحلة الجوية المعروف لدينا تلقائيًا حالة عدم حضور للراكب.

**تعديل الحجز**

تخضع التعديلات للتوافر. نوضح أي سعر معدّل قبل موافقتك على التغيير.

**معالجة المبالغ المستردة**

نبدأ إجراء الاسترداد إلى وسيلة الدفع الأصلية خلال 5 أيام عمل من تأكيد المبلغ المسترد. قد يستغرق البنك أو مزوّد الدفع وقتًا إضافيًا لإيداع المبلغ.

**كيفية إلغاء الحجز أو تعديله**

أرسل بريدًا إلكترونيًا إلى info@airportandcitytransfer.com مع ذكر مرجع الحجز. للتغييرات العاجلة، اتصل أيضًا على +44 208 153 0303. تُحسب مهلة الإلغاء من وقت استلام ACT للطلب وبالاستناد إلى موعد الاستلام المؤكد، وليس من وقت رد الموظفين.

**Cancellation FAQ**

نعم. إذا استلمت ACT طلب الإلغاء قبل موعد الاستلام المؤكد بـ24 ساعة على الأقل، يُرد المبلغ كاملًا. خلال الـ24 ساعة السابقة للاستلام، يجوز خصم الخسائر المعقولة والمثبتة الناتجة عن الإلغاء، بحد أقصى قيمة الحجز، مع مراعاة التكاليف التي تم توفيرها أو العمل البديل. تخضع التعديلات للتوافر، ويتطلب أي سعر معدّل موافقتك. أرسل بريدًا إلى info@airportandcitytransfer.com مع مرجع الحجز، واتصل على +44 208 153 0303 للتغييرات العاجلة. راجع الشروط والأحكام لتفاصيل الانتظار وعدم الحضور ومعالجة الاسترداد.

**Flight FAQ**

تواصل مع ACT عند تأخر رحلتك الجوية أو إلغائها، لنراجع ترتيبات الاستلام المعدّلة ونتفق عليها. لا يُعتبر تأخر الرحلة الجوية المعروف لدينا تلقائيًا حالة عدم حضور للراكب.

**Payment notice**

إذا استلمنا الإلغاء قبل الاستلام بـ24 ساعة على الأقل: استرداد كامل. خلال الـ24 ساعة السابقة للاستلام أو عند عدم الحضور، يجوز خصم الخسائر المعقولة والمثبتة، بحد أقصى قيمة الحجز، مع مراعاة التكاليف التي تم توفيرها أو العمل البديل. يرجى قراءة الشروط والأحكام قبل الدفع.

### French

**Annulation au moins 24 heures avant la prise en charge**

Si ACT reçoit votre annulation au moins 24 heures avant l’heure de prise en charge confirmée, y compris exactement 24 heures avant, vous bénéficiez d’un remboursement intégral.

**Annulation moins de 24 heures avant la prise en charge**

ACT peut déduire les pertes raisonnables et justifiées directement causées par votre annulation, dans la limite du prix de la réservation. Nous prenons des mesures raisonnables pour réduire ces pertes et tenons compte des coûts économisés ou des prestations de remplacement obtenues. Le solde éventuel vous est remboursé.

**Absence du passager**

Une absence n’est constatée qu’après le délai d’attente convenu et des tentatives documentées de contacter le passager. Toute retenue suit la même règle fondée sur les pertes que pour une annulation à moins de 24 heures et reste limitée au prix de la réservation.

**Délais d’attente**

Le délai d’attente est de 15 minutes pour les prises en charge ordinaires et de 60 minutes pour les prises en charge à l’aéroport, à compter de l’heure de prise en charge convenue. Tous frais d’attente supplémentaires doivent être annoncés et acceptés.

**Si ACT ne peut pas assurer le trajet**

Nous vous proposons une solution de remplacement à accepter, ou un remboursement intégral du trajet qui ne peut pas être assuré.

**Retards ou annulations de vols**

Contactez ACT en cas de changement concernant votre vol. Nous examinons et convenons de nouvelles modalités de prise en charge. Un retard de vol connu n’est pas automatiquement considéré comme une absence du passager.

**Modification de réservation**

Les modifications dépendent des disponibilités. Tout nouveau prix vous est communiqué avant votre acceptation de la modification.

**Traitement des remboursements**

Nous lançons le remboursement sur le moyen de paiement d’origine dans les 5 jours ouvrés suivant la confirmation du montant à rembourser. Votre banque ou prestataire de paiement peut prendre davantage de temps pour créditer les fonds.

**Comment annuler ou modifier une réservation**

Envoyez un e-mail à info@airportandcitytransfer.com en indiquant votre référence de réservation. Pour les changements urgents, appelez également le +44 208 153 0303. Le délai d’annulation est calculé à partir de la réception de votre demande par ACT, par rapport à l’heure de prise en charge confirmée, et non à partir de la réponse de notre équipe.

**Cancellation FAQ**

Oui. Si ACT reçoit votre annulation au moins 24 heures avant l’heure de prise en charge confirmée, vous bénéficiez d’un remboursement intégral. À moins de 24 heures, des pertes raisonnables et justifiées peuvent être déduites, dans la limite du prix de la réservation, en tenant compte des coûts économisés ou des prestations de remplacement obtenues. Les modifications dépendent des disponibilités ; tout nouveau prix nécessite votre accord. Écrivez à info@airportandcitytransfer.com avec votre référence de réservation et appelez le +44 208 153 0303 pour les changements urgents. Consultez les conditions générales pour les délais d’attente, les absences et le traitement des remboursements.

**Flight FAQ**

Contactez ACT en cas de retard ou d’annulation de votre vol afin de convenir de nouvelles modalités de prise en charge. Un retard de vol connu n’est pas automatiquement considéré comme une absence du passager.

**Payment notice**

Annulation reçue au moins 24 heures avant la prise en charge : remboursement intégral. À moins de 24 heures ou en cas d’absence, des pertes raisonnables et justifiées peuvent être déduites, dans la limite du prix de la réservation et en tenant compte des coûts économisés ou des prestations de remplacement obtenues. Veuillez lire les conditions générales avant de payer.

## Next task

Align the customer-visible instruction PDF/booking notices with these approved
rules and prepare the smallest policy release for approval. French provider and
other service-claim gates remain separate; this policy approval does not authorise
enabling French or deploying main.
