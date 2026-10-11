/// The API stores UTC timestamps without a timezone suffix in older records.
/// Interpret those as UTC before displaying them in the phone's local time.
DateTime? parseServerTime(Object? value) {
  final text = value?.toString();
  if (text == null || text.isEmpty) return null;
  final hasZone = RegExp(r'(?:Z|[+-]\d{2}:\d{2})$', caseSensitive: false)
      .hasMatch(text);
  return DateTime.tryParse(hasZone ? text : '${text}Z')?.toLocal();
}
