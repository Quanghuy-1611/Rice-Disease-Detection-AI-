class IpmAdvice {
  const IpmAdvice({
    required this.recommendation,
    required this.organicMethods,
    required this.chemicalMethods,
    required this.thresholdReached,
  });

  final String recommendation;
  final List<String> organicMethods;
  final List<String> chemicalMethods;
  final bool thresholdReached;

  factory IpmAdvice.fromApi(Object? value) {
    if (value is Map) {
      return IpmAdvice(
        recommendation: _text(value['recommendation']),
        organicMethods: _methods(value['organic_methods']),
        chemicalMethods: _methods(value['chemical_methods']),
        thresholdReached: value['threshold_reached'] == true,
      );
    }
    return IpmAdvice(
      recommendation: _text(value),
      organicMethods: const [],
      chemicalMethods: const [],
      thresholdReached: false,
    );
  }

  static String _text(Object? value) => value is String ? value.trim() : '';

  static List<String> _methods(Object? value) {
    if (value is! List) return const [];
    return value
        .whereType<String>()
        .map((method) => method.trim())
        .where((method) => method.isNotEmpty)
        .toList();
  }
}
