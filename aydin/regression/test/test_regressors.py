import time
from os.path import join
import numpy
import pytest
from skimage.data import camera
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

from aydin.features.standard_features import StandardFeatureGenerator
from aydin.io.datasets import normalise, add_noise
from aydin.io.folders import get_temp_folder
from aydin.regression.base import RegressorBase
from aydin.regression.cb import CBRegressor
from aydin.regression.lgbm import LGBMRegressor
from aydin.regression.linear import LinearRegressor
from aydin.regression.perceptron import PerceptronRegressor
from aydin.regression.random_forest import RandomForestRegressor
from aydin.regression.support_vector import SupportVectorRegressor


@pytest.fixture(scope="session")
def data():
    image = camera()[:256, :256].astype(numpy.float32)
    image = normalise(image)
    noisy = add_noise(image)

    # feature generator requires images in 'standard' form: BCTZYX
    noisy = noisy[numpy.newaxis, numpy.newaxis, ...]

    generator = StandardFeatureGenerator(max_level=6)

    features = generator.compute(noisy, exclude_center_value=True)

    x = features.reshape(-1, features.shape[-1])
    y = noisy.reshape(-1)

    return image, noisy, x, y


def test_linear_regressor(data):
    with_regressor(data, LinearRegressor(), min_ssim=0.6)


def test_rf_regressor(data):
    with_regressor(data, RandomForestRegressor(), min_ssim=0.6)


def test_svr_regressor(data):
    with_regressor(data, SupportVectorRegressor(), min_ssim=0.65)


def test_lgbm_regressor(data):
    with_regressor(data, LGBMRegressor(max_num_estimators=600), min_ssim=0.75)


def test_cb_regressor(data):
    with_regressor(data, CBRegressor(max_num_estimators=600), min_ssim=0.75)


def test_nn_regressor(data):
    with_regressor(data, PerceptronRegressor(max_epochs=6, depth=6), min_ssim=0.64)


def with_regressor(data, regressor, min_ssim=0.8):
    image, noisy, x, y = data

    regressor.fit(x, y)

    yp = regressor.predict(x)

    denoised = yp.reshape(image.shape)

    denoised = numpy.clip(denoised, 0, 1)

    ssim_value = ssim(denoised, image)
    psnr_value = psnr(image, denoised)

    print("denoised", psnr_value, ssim_value)

    assert ssim_value > min_ssim

    # Test saveload
    temp_file = join(get_temp_folder(), "test_reg_saveload.json" + str(time.time()))
    regressor.save(temp_file)

    del regressor

    loaded_regressor = RegressorBase.load(temp_file)

    yp = loaded_regressor.predict(x)

    denoised = yp.reshape(image.shape)

    # print(numpy.min(denoised), numpy.min(image))
    # print(numpy.max(denoised), numpy.max(image))
    denoised = denoised.clip(0, 1)
    ssim_value = ssim(denoised, image)
    psnr_value = psnr(image, denoised)

    print("denoised", psnr_value, ssim_value)

    assert ssim_value > min_ssim
