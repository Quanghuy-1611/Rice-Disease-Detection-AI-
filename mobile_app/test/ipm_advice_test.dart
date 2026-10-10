import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/models/ipm_advice.dart';

void main() {
  test('parses the seven-class API IPM response into display fields', () {
    final advice = IpmAdvice.fromApi({
      'recommendation': 'Cỏ dại mọc rải rác.',
      'organic_methods': [' Làm cỏ bằng tay ', 'Giữ nước để ém cỏ'],
      'chemical_methods': ['Phun điểm khi cần'],
      'threshold_reached': false,
    });

    expect(advice.recommendation, 'Cỏ dại mọc rải rác.');
    expect(advice.organicMethods, ['Làm cỏ bằng tay', 'Giữ nước để ém cỏ']);
    expect(advice.chemicalMethods, ['Phun điểm khi cần']);
    expect(advice.thresholdReached, isFalse);
  });

  test('missing or malformed advice never renders a raw map', () {
    final advice = IpmAdvice.fromApi({'organic_methods': 'invalid'});
    expect(advice.recommendation, isEmpty);
    expect(advice.organicMethods, isEmpty);
    expect(advice.chemicalMethods, isEmpty);
  });
}
